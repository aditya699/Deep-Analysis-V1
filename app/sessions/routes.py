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
                   async for session in collection.find({"user_email": email}).sort("created_at", -1)]  # Add this line
        if not sessions:
            return {"sessions": [], "count": 0}
        return {"sessions": sessions, "count": len(sessions)}
    except Exception as e:
        await log_error(error=e, location="get_all_sessions", additional_info={"user_email": current_user.get("email")})
        raise HTTPException(status_code=500, detail="Internal server error")
    
@router.get("/get_session_by_id")
async def get_session_by_id(session_id: str, current_user: dict = Depends(get_current_user), db: Database = Depends(get_db)):
    try:
        email = current_user["email"]
        collection = db["csv_sessions"]
        session = await collection.find_one({"user_email": email, "session_id": session_id})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        # Convert ObjectId to string and handle other fields
        return {"_id": str(session["_id"]) if "_id" in session else None, **{k: v for k, v in session.items() if k != "_id"}}
    except Exception as e:
        await log_error(error=e, location="get_session_by_id", additional_info={"user_email": current_user.get("email"), "session_id": session_id})
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/delete_session")
async def delete_session(session_id: str, current_user: dict = Depends(get_current_user), db: Database = Depends(get_db)):

    try:
        email = current_user["email"]
        collection = db["csv_sessions"]
        
        # First verify the session exists and belongs to the user
        session = await collection.find_one({"user_email": email, "session_id": session_id})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Delete associated chat messages first
        await db["messages"].delete_many({"session_id": session_id})
        
        # Delete the session
        result = await collection.delete_one({"user_email": email, "session_id": session_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=500, detail="Failed to delete session")
            
        return {"message": "Session deleted successfully"}
    except Exception as e:
        await log_error(error=e, location="delete_session", additional_info={"user_email": current_user.get("email"), "session_id": session_id})
        raise HTTPException(status_code=500, detail="Internal server error")
    
@router.get("/get_session_messages")
async def get_session_messages(
    session_id: str, 
    current_user: dict = Depends(get_current_user), 
    db: Database = Depends(get_db)
):
    try:
        # Verify session belongs to user
        session = await db["csv_sessions"].find_one({
            "user_email": current_user["email"], 
            "session_id": session_id
        })
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get messages
        messages = await db["messages"].find(
            {"session_id": session_id}
        ).sort("created_at", 1).to_list(length=None)
        
        # Convert ObjectId to string for each message
        formatted_messages = []
        for message in messages:
            formatted_message = {"_id": str(message["_id"]) if "_id" in message else None, **{k: v for k, v in message.items() if k != "_id"}}
            formatted_messages.append(formatted_message)
        
        return {"messages": formatted_messages, "count": len(formatted_messages)}
    except Exception as e:
        await log_error(error=e, location="get_session_messages", additional_info={"session_id": session_id})
        raise HTTPException(status_code=500, detail="Internal server error")