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
            }}
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
        except Exception as e:
            await log_error(e, "deep_analysis/routes.py", "deep_analysis")
            raise HTTPException(status_code=500, detail="Error parsing KPI list")
        
        #Update the session status with the kpi list
        await deep_analysis_collection.update_one(
            {"session_id": session_id}, 
            {"$set": {
                "kpi_list": kpi_list,
                "status": "Deep Analysis KPI List Generated",
                "updated_at": datetime.now()
            }}
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
            """
            
            #Generate response for the kpi with code interpreter
            kpi_response = await openai_client.responses.create(
                model="gpt-4.1-mini",
                tools=[{"type": "code_interpreter", "container": container_id}],
                tool_choice="auto",
                input=prompt_kpi
            )

            # Initialize variables for code and chart handling
            code_content = None
            code_explanation = None
            chart_url = None

            # Process the response
            for output in kpi_response.output:
                # Extract code if available
                if hasattr(output, 'code') and output.code:
                    code_content = output.code
                    
                    # Generate code explanation
                    code_explanation_response = await openai_client.responses.create(
                        model="gpt-4.1-mini",
                        input=f"Explain what the following code is doing so that the business user can understand it. Format your explanation as a numbered list where each step starts with 'This code does:' followed by the action: {code_content}"
                    )
                    code_explanation = code_explanation_response.output_text

                # Handle chart generation
                if hasattr(output, 'content'):
                    for content in output.content:
                        if hasattr(content, 'annotations'):
                            for annotation in content.annotations:
                                if annotation.type == 'container_file_citation':
                                    file_id = annotation.file_id
                                    # Download the chart and upload to blob storage
                                    chart_url = await download_file_from_container(file_id, container_id, blob_client)
            
            #Create KPI analysis object
            kpi_analysis = {
                "kpi_name": kpi,
                "analysis": kpi_response.output_text,
                "code": code_content,
                "code_explanation": code_explanation,
                "chart_url": chart_url,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            kpi_analyses.append(kpi_analysis)
            
            #Update the session status with the latest KPI analysis
            await deep_analysis_collection.update_one(
                {"session_id": session_id},
                {"$push": {
                    "kpi_analyses": kpi_analysis
                },
                "$set": {
                    "status": f"Deep Analysis - Analyzing KPI: {kpi}",
                    "updated_at": datetime.now()
                }}
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

        # Create master data dictionary for report generation
        master_data_dict = {
            "summary": summary
        }
        
        # Add each KPI analysis to the master data dictionary
        for analysis in kpi_analyses:
            master_data_dict[analysis["kpi_name"]] = {
                "analysis": analysis["analysis"],
                "code_explanation": analysis["code_explanation"],
                "visualization": {
                    "visualization_url": analysis["chart_url"]
                }
            }

        # Generate HTML report
        html_content = create_html_report(master_data_dict)
        
        # Upload report to blob storage
        report_url = await upload_report_to_blob(html_content, blob_client, session_id)

        #Final update to mark analysis as complete
        await deep_analysis_collection.update_one(
            {"session_id": session_id},
            {"$set": {
                "status": "Deep Analysis Complete",
                "report_url": report_url,
                "updated_at": datetime.now()
            }}
        )

        return {
            "blob_url": blob_url, 
            "csv_info": csv_info, 
            "file_path": file_path,
            "kpi_list": kpi_list,
            "kpi_analyses": kpi_analyses,
            "report_url": report_url
        }
    except Exception as e:
        await log_error(e, "deep_analysis/routes.py", "deep_analysis")
        raise HTTPException(status_code=500, detail="Error during deep analysis")