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
        kpi_list = kpi_list_response.output[0].content[0].model_dump()['text']
        
        #Update the session status with the kpi list
        await deep_analysis_collection.update_one(
            {"session_id": session_id}, 
            {"$set": {
                "kpi_list": kpi_list,
                "status": "Deep Analysis KPI List Generated",
                "updated_at": datetime.now()
            }}
        )


        return {"blob_url": blob_url, "csv_info": csv_info, "file_path": file_path,"kpi_list": kpi_list}
    except Exception as e:
        await log_error(e, "deep_analysis/routes.py", "deep_analysis")
        raise HTTPException(status_code=500, detail="Error during deep analysis")