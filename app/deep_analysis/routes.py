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
from app.deep_analysis.schemas import KPIList, KPIAnalysis
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
            }},
            sort={"created_at": -1}
        )
        
        #Generate KPI List for Manager Agent
        prompt_kpi_list = MANAGER_PROMPT+f"\n\nInformation about the dataset: {csv_info}"

        kpi_list_response = await openai_client.responses.parse(
                model="gpt-4.1-mini",
                input=prompt_kpi_list,
                text_format=KPIList
            )
        
        kpi_list = kpi_list_response.output_parsed.kpi_list
        kpi_list=kpi_list[:10]
        print(f"Generated KPI List: {kpi_list}")
        
        #Update the session status with the kpi list and their status
        await deep_analysis_collection.update_one(
            {"session_id": session_id}, 
            {"$set": {
                "kpi_list": kpi_list,
                "status": "Deep Analysis KPI List Generated",
                "updated_at": datetime.now()
            }},
            sort={"created_at": -1}
        )

        for kpi in kpi_list:
            print(f"Analyzing KPI: {kpi}")
            
            #Generate prompt for the kpi with explicit chart creation instruction
            prompt_kpi = f"""
            You are a data analyst tasked with analyzing a specific KPI from a dataset.
            
            Your task:
            1. Analyze the KPI: {kpi}
            2. Use the dataset located at: {file_path}
            3. Sample data preview: {csv_info}
            
            Instructions:
            - Provide detailed insights about this KPI
            - ALWAYS create and save a visualization chart for this KPI using matplotlib or seaborn
            - Make sure to use plt.show() to display and save the chart
            - Explain your findings in business terms
            - The chart must be generated as part of your analysis
            
            CRITICAL: You must create a visual chart/graph for this KPI analysis.
            """
            
            #Generate response for the kpi with code interpreter
            kpi_response = await openai_client.responses.create(
                model="gpt-4.1-mini",
                tools=[{"type": "code_interpreter", "container": container_id}],
                tool_choice="required",
                input=prompt_kpi
            )
            
            print(f"KPI Response received for {kpi}")
            print(f"Response outputs count: {len(kpi_response.output) if kpi_response.output else 0}")
            
            # Improved chart extraction logic
            chart_url = None
            chart_file_id = None
            
            try:
                for i, output in enumerate(kpi_response.output):
                    print(f"Processing output {i}: type={type(output)}")
                    
                    # Check if this is a message output with content and annotations
                    if hasattr(output, 'content') and output.content:
                        for j, content in enumerate(output.content):
                            print(f"  Content {j}: type={type(content)}, hasAnnotations={hasattr(content, 'annotations')}")
                            
                            if hasattr(content, 'annotations') and content.annotations:
                                print(f"    Found {len(content.annotations)} annotations")
                                for k, annotation in enumerate(content.annotations):
                                    print(f"    Annotation {k}: type={getattr(annotation, 'type', 'no_type')}")
                                    
                                    if (hasattr(annotation, 'type') and 
                                        annotation.type == 'container_file_citation' and
                                        hasattr(annotation, 'file_id')):
                                        chart_file_id = annotation.file_id
                                        print(f"Found chart file ID: {chart_file_id}")
                                        break
                                        
                                if chart_file_id:
                                    break
                        if chart_file_id:
                            break
                    
                    # Check if this is a code interpreter tool call with outputs
                    elif hasattr(output, 'type') and output.type == 'code_interpreter_call':
                        print(f"  Found code interpreter call")
                        if hasattr(output, 'outputs') and output.outputs:
                            print(f"    Has {len(output.outputs)} outputs")
                            for tool_output in output.outputs:
                                if (hasattr(tool_output, 'type') and 
                                    tool_output.type == 'image' and
                                    hasattr(tool_output, 'image') and
                                    hasattr(tool_output.image, 'file_id')):
                                    chart_file_id = tool_output.image.file_id
                                    print(f"Found chart file ID from tool output: {chart_file_id}")
                                    break
                            if chart_file_id:
                                break
                    
                    # Additional check for response code interpreter tool call structure
                    elif hasattr(output, '__class__') and 'CodeInterpreter' in str(output.__class__):
                        print(f"  Found ResponseCodeInterpreterToolCall")
                        # Sometimes the file citation is in the response structure differently
                        if hasattr(output, 'results') and output.results:
                            for result in output.results:
                                if hasattr(result, 'type') and result.type == 'image':
                                    if hasattr(result, 'image') and hasattr(result.image, 'file_id'):
                                        chart_file_id = result.image.file_id
                                        print(f"Found chart file ID from results: {chart_file_id}")
                                        break
                            if chart_file_id:
                                break

                # Download the chart if file ID was found
                if chart_file_id:
                    print(f"Attempting to download chart with file ID: {chart_file_id}")
                    chart_url = await download_file_from_container(chart_file_id, container_id, blob_client)
                    print(f"Chart URL successfully extracted: {chart_url}")
                else:
                    print(f"No chart file found in response for KPI: {kpi}")
                    
            except Exception as e:
                print(f"Error extracting chart for KPI {kpi}: {str(e)}")
                chart_url = None

            #Pass the response for another openai call to get the analysis
            analysis_prompt = f"""
            You are an analyst who needs to make sense of work done by another analyst.
            For the analysis you need to extract:

            1. Business insights
            2. Code
            3. Code explanation in a paragraph
            4. How did agent compute the KPI in a paragraph

            Response: {str(kpi_response)}
            """
            
            # Prepare input content - only include image if chart_url is available
            input_content = [{"type": "input_text", "text": analysis_prompt}]
            if chart_url:
                print(f"Including chart in analysis for KPI: {kpi}")
                input_content.append({
                    "type": "input_image",
                    "image_url": chart_url,
                })
            else:
                print(f"No chart to include in analysis for KPI: {kpi}")
            
            analysis_response = await openai_client.responses.parse(
                model="gpt-4.1-mini",
                input=[{
                    "role": "user",
                    "content": input_content,
                }],
                text_format=KPIAnalysis
            )
            
            #Create KPI analysis object
            kpi_analysis = {
                "kpi_name": kpi,
                "business_analysis": analysis_response.output_parsed.business_analysis,
                "code": analysis_response.output_parsed.code,
                "code_explanation": analysis_response.output_parsed.code_explanation,
                "chart_url": chart_url,
                "analysis_steps": analysis_response.output_parsed.analysis_steps,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            print(f"KPI analysis completed for {kpi}. Chart URL: {chart_url}")
            
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
                sort={"created_at": -1}
            )

        #Get all the kpi analyses after processing all KPIs
        session_data = await deep_analysis_collection.find_one({"session_id": session_id})
        kpi_analyses = session_data.get("kpi_analyses", [])

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
            sort={"created_at": -1}
        )

        # Generate HTML report by pulling data from DB
        html_content = await create_html_report(session_id)
        
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
            sort={"created_at": -1}
        )

        return {
            "report_url": report_url
        }
        
    except Exception as e:
        await log_error(e, "deep_analysis/routes.py", "deep_analysis")
        raise HTTPException(status_code=500, detail="Error during deep analysis")
    

@router.get("/deep_analysis/status/{session_id}")
async def get_deep_analysis_status(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    try:
        deep_analysis_collection = db["deep_analysis"]
        
        # Find the most recent session document
        session_data = await deep_analysis_collection.find_one(
            {"session_id": session_id},
            sort=[("created_at", -1)]
        )
        
        if not session_data:
            raise HTTPException(status_code=404, detail="Deep analysis session not found")
            
        # Extract relevant status information
        status_info = {
            "status": session_data.get("status", "Unknown"),
            "kpi_list": session_data.get("kpi_list", []),
            "kpi_status": session_data.get("kpi_status", {}),
            "report_url": session_data.get("report_url"),
            "created_at": session_data.get("created_at"),
            "updated_at": session_data.get("updated_at")
        }
        
        return status_info
        
    except Exception as e:
        await log_error(e, "deep_analysis/routes.py", "get_deep_analysis_status")
        raise HTTPException(status_code=500, detail="Error fetching deep analysis status")
    

