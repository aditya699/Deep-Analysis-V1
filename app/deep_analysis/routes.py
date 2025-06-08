from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import List, Dict, Any
import uuid
from app.auth.utils import get_current_user
from app.db.mongo import get_db
from pymongo.database import Database
import pandas as pd
from io import StringIO
from datetime import datetime
from azure.core.exceptions import AzureError
from azure.storage.blob.aio import BlobServiceClient
from app.core.config import settings
from app.db.mongo import log_error
from app.chat.schemas import UploadCSVResponse, ChatResponse, SmartQuestions
from app.container.utils import get_all_active_containers, upload_file_to_container
import base64
from azure.storage.blob import BlobBlock
from app.llm.openai_client import get_openai_client
from openai import OpenAI
from app.db.blob import get_blob_client
from app.chat.utils import download_file_from_container
from app.deep_analysis.prompts import MANAGER_PROMPT
from app.deep_analysis.schemas import KPIList
from app.deep_analysis.report import create_html_report, upload_report_to_blob

def process_openai_response(response):
    """Process OpenAI response to extract code, analysis, and chart information."""
    analysis_steps = []
    code_content = None
    chart_file_id = None
    analysis_text = []
    
    for output in response.output:
        step = {
            'type': output.type,
            'content': None,
            'code': None,
            'chart_file_id': None
        }
        
        # Handle code interpreter calls
        if output.type == "code_interpreter_call" and hasattr(output, 'code'):
            step['code'] = output.code
            if not code_content:  # Only store the first code block
                code_content = output.code
            analysis_steps.append(step)
            continue
            
        # Handle regular messages
        if hasattr(output, 'content'):
            for content in output.content:
                if not hasattr(content, 'text'):
                    continue
                    
                text = content.text
                
                # Check for chart annotations
                if hasattr(content, 'annotations'):
                    for annotation in content.annotations:
                        if annotation.type == 'container_file_citation':
                            step['chart_file_id'] = annotation.file_id
                            chart_file_id = annotation.file_id
                
                # Check if this is code (starts with import or #)
                if text.strip().startswith(('import ', '# ')):
                    step['code'] = text
                    if not code_content:  # Only store the first code block
                        code_content = text
                else:
                    # This is analysis text
                    step['content'] = text
                    analysis_text.append(text)
            
            # Only add the step if it has content or code
            if step['content'] or step['code']:
                analysis_steps.append(step)
    
    # Combine all analysis text, excluding code blocks
    analysis = '\n'.join(text for text in analysis_text if not text.strip().startswith(('import ', '# ')))
    
    return {
        'code': code_content,
        'analysis': analysis,
        'chart_file_id': chart_file_id,
        'analysis_steps': analysis_steps
    }

router = APIRouter()

@router.post("/deep_analysis")
async def deep_analysis(
        session_id: str,
        current_user: dict = Depends(get_current_user),
        db: Database = Depends(get_db),
        container_id: str = Depends(get_all_active_containers),
        openai_client: OpenAI = Depends(get_openai_client),
        blob_client: BlobServiceClient = Depends(get_blob_client)
):
    try:
        """
        This endpoint will be main endpoint to control deep analysis.
        """
        #From the session_id , we need the blob url
        sessions_collection = db["csv_sessions"]
        deep_analysis_collection = db["deep_analysis"]

        #From sessions find the blob url 
        session_doc = await sessions_collection.find_one({"session_id": session_id})
        
        if not session_doc:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Extract blob URL from file_info
        blob_url = session_doc.get("file_info", {}).get("file_url")
        
        if not blob_url:
            raise HTTPException(status_code=404, detail="Blob URL not found in session")
        
        #Extract csv information from the session document
        csv_info = session_doc.get("csv_info", {})
        
        #Create initial deep analysis session status
        session_status={
            "session_id": session_id,
            "user_email": current_user.get("email"),
            "user_id": current_user.get("id"),
            "file_path": None,
            "status": "Deep Analysis Started",
            "csv_info": csv_info,
            "blob_url": blob_url,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "kpi_list": None
        }
        await deep_analysis_collection.insert_one(session_status)
        
        #Upload the file to the container
        file_path = await upload_file_to_container(container_id, blob_url)

        #Update the session status after file upload
        await deep_analysis_collection.update_one(
            {"session_id": session_id},
            {"$set": {
                "file_path": file_path,
                "status": "Deep Analysis File Uploaded",
                "updated_at": datetime.now()
            }},
            sort={"created_at": -1}  # Use dictionary for sort
        )
        
        #Generate KPI List for Manager Agent
        prompt_kpi_list = MANAGER_PROMPT+f"\n\nInformation about the dataset: {csv_info}"

        kpi_list_response = await openai_client.responses.create(
                model="gpt-4.1-mini",
                input=prompt_kpi_list
            )
        
        #From the kpi list response, we need to extract the kpi list
        kpi_text = kpi_list_response.output[0].content[0].model_dump()['text']
        
        # Parse the text response into a proper list
        try:
            # Remove any leading/trailing whitespace and quotes
            kpi_text = kpi_text.strip()
            # Remove the outer brackets and split by commas
            kpi_text = kpi_text.strip('[]')
            kpi_list = [kpi.strip().strip('"\'') for kpi in kpi_text.split(',') if kpi.strip()]
            
            # Create a dictionary to track KPI analysis status
            kpi_status = {kpi: 0 for kpi in kpi_list}
        except Exception as e:
            await log_error(e, "deep_analysis/routes.py", "deep_analysis")
            raise HTTPException(status_code=500, detail="Error parsing KPI list")
        
        #Update the session status with the kpi list and their status
        await deep_analysis_collection.update_one(
            {"session_id": session_id}, 
            {"$set": {
                "kpi_list": kpi_list,
                "kpi_status": kpi_status,
                "status": "Deep Analysis KPI List Generated",
                "updated_at": datetime.now()
            }},
            sort={"created_at": -1}  # Use dictionary for sort
        )

        #Iterate over kpi list
        kpi_list=kpi_list[:2] #Filter for testing
        kpi_analyses = []

        for kpi in kpi_list:
            print("Analyzing KPI: ", kpi)
            #Generate prompt for the kpi
            prompt_kpi = f"""
            You are a data analyst tasked with analyzing a specific KPI from a dataset.
            
            Your task:
            1. Analyze the KPI: {kpi}
            2. Use the dataset located at: {file_path}
            3. Sample data preview: {csv_info}
            
            Instructions:
            - Provide detailed insights about this KPI
            - Create a chart if it is beneficial
            - Explain your findings in business terms
            
            Focus on actionable insights that would be valuable for business decision-making.
            Do not ask follow up questions, just provide the analysis.
            """
            
            #Generate response for the kpi with code interpreter
            kpi_response = await openai_client.responses.create(
                model="gpt-4.1-mini",
                tools=[{"type": "code_interpreter", "container": container_id}],
                tool_choice="auto",
                input=prompt_kpi
            )

            # Dump kpi_response to txt file for debugging
            import json
            import os
            debug_dir = "debug_dumps"
            os.makedirs(debug_dir, exist_ok=True)
            
            # Create a comprehensive dump of the response object
            debug_info = {
                "kpi_name": kpi,
                "response_type": str(type(kpi_response)),
                "response_dir": dir(kpi_response),
                "response_dict": None,
                "output_info": [],
                "raw_response": str(kpi_response)
            }
            
            # Try to get dict representation if available
            try:
                if hasattr(kpi_response, 'model_dump'):
                    debug_info["response_dict"] = kpi_response.model_dump()
                elif hasattr(kpi_response, '__dict__'):
                    debug_info["response_dict"] = kpi_response.__dict__
            except Exception as e:
                debug_info["dict_error"] = str(e)
            
            # Analyze output structure
            if hasattr(kpi_response, 'output'):
                for i, output in enumerate(kpi_response.output):
                    output_info = {
                        "index": i,
                        "type": str(type(output)),
                        "dir": dir(output),
                        "attributes": {}
                    }
                    
                    # Check common attributes
                    for attr in ['code', 'content', 'text', 'annotations']:
                        if hasattr(output, attr):
                            try:
                                attr_value = getattr(output, attr)
                                output_info["attributes"][attr] = {
                                    "type": str(type(attr_value)),
                                    "value": str(attr_value)[:500] if attr_value else None  # Truncate long values
                                }
                            except Exception as e:
                                output_info["attributes"][attr] = {"error": str(e)}
                    
                    debug_info["output_info"].append(output_info)
            
            # Write debug info to file
            debug_filename = f"{debug_dir}/kpi_response_debug_{kpi.replace(' ', '_').replace('/', '_')}.txt"
            with open(debug_filename, 'w', encoding='utf-8') as f:
                f.write(json.dumps(debug_info, indent=2, default=str))
            
            print(f"🐛 Debug dump created: {debug_filename}")

            # Process the response
            response_data = process_openai_response(kpi_response)
            
            # Generate code explanation if we have code
            if response_data['code']:
                code_explanation_response = await openai_client.responses.create(
                    model="gpt-4.1-mini",
                    input=f"Explain what the following code is doing so that the business user can understand it. Format your explanation as a numbered list where each step starts with 'This code does:' followed by the action: {response_data['code']}"
                )
                code_explanation = code_explanation_response.output_text
            
            # Download and upload chart if we have a file ID
            chart_url = None
            if response_data['chart_file_id']:
                chart_url = await download_file_from_container(response_data['chart_file_id'], container_id, blob_client)
            
            #Create KPI analysis object
            kpi_analysis = {
                "kpi_name": kpi,
                "analysis": response_data['analysis'],
                "code": response_data['code'],
                "code_explanation": code_explanation,
                "chart_url": chart_url,
                "analysis_steps": response_data['analysis_steps'],
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            kpi_analyses.append(kpi_analysis)
            
            #Update the session status with the latest KPI analysis and mark it as complete
            await deep_analysis_collection.update_one(
                {"session_id": session_id},
                {"$push": {
                    "kpi_analyses": kpi_analysis
                },
                "$set": {
                    f"kpi_status.{kpi}": 1,  # Mark this KPI as analyzed
                    "status": f"Deep Analysis - Analyzing KPI: {kpi}",
                    "updated_at": datetime.now()
                }},
                sort={"created_at": -1}  # Use dictionary for sort
            )

        # Generate summary using OpenAI
        summary_prompt = f"""
        Based on the following KPI analyses, provide a concise executive summary that highlights the key findings and insights:
        
        {kpi_analyses}
        
        Focus on the most important trends, patterns, and actionable insights that would be valuable for business decision-making.
        """
        
        summary_response = await openai_client.responses.create(
            model="gpt-4.1-mini",
            input=summary_prompt
        )
        
        summary = summary_response.output_text

        # Update the session with the summary
        await deep_analysis_collection.update_one(
            {"session_id": session_id},
            {"$set": {
                "summary": summary,
                "status": "Deep Analysis - Generating Report",
                "updated_at": datetime.now()
            }},
            sort={"created_at": -1}  # Use dictionary for sort
        )

        # Generate HTML report by pulling data from DB
        html_content = await create_html_report(session_id, deep_analysis_collection)
        
        # Upload report to blob storage
        report_url = await upload_report_to_blob(html_content, blob_client, session_id)

        #Final update to mark analysis as complete
        await deep_analysis_collection.update_one(
            {"session_id": session_id},
            {"$set": {
                "status": "Deep Analysis Complete",
                "report_url": report_url,
                "updated_at": datetime.now()
            }},
            sort={"created_at": -1}  # Use dictionary for sort
        )

        return {
            "report_url": report_url
        }
    except Exception as e:
        await log_error(e, "deep_analysis/routes.py", "deep_analysis")
        raise HTTPException(status_code=500, detail="Error during deep analysis")