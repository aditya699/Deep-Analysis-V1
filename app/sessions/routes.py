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
from app.chat.schemas import UploadCSVResponse
from app.sessions.schemas import GetAllSessions

router = APIRouter()

@router.get("/get_all_sessions")
async def get_all_sessions(current_user: dict = Depends(get_current_user), db: Database = Depends(get_db)):
    try:
        email = current_user["email"]
        collection = db["csv_sessions"]
        sessions = [{"_id": str(session["_id"]) if "_id" in session else None, **{k: v for k, v in session.items() if k != "_id"}} 
                   async for session in collection.find({"user_email": email})]
        if not sessions:
            raise HTTPException(status_code=404, detail="No sessions found")
        return sessions
    except Exception as e:
        await log_error(error=e, location="get_all_sessions", additional_info={"user_email": current_user.get("email")})
        raise HTTPException(status_code=500, detail="Internal server error")
    
    
    