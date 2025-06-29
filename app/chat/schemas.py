from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class FileInfo(BaseModel):
    """File metadata information"""
    original_filename: str
    blob_name: str
    container_name: str
    file_url: str
    file_size: int
    content_type: str = "text/csv"

class CSVInfo(BaseModel):
    total_columns: int
    column_names: List[str]
    preview_data: List[Dict[str, Any]]

class CSVSession(BaseModel):
    session_id: str
    user_email: str
    user_id: str
    file_info: FileInfo
    csv_info: CSVInfo
    smart_questions: List[str]
    created_at: datetime
    updated_at: datetime
    status: str = "active"

class UploadCSVResponse(BaseModel):
    """Response model for CSV upload endpoint"""
    session_id: str
    file_url: str
    file_name: str
    preview_data: List[Dict[str, Any]]
    file_info: FileInfo
    smart_questions: List[str]
    message: str
    success: bool

class ChatMessage(BaseModel):
    """Chat message model"""
    #_id will be generated by the database and that will be the message id
    session_id: str  #foreign key(vibe wise)
    role: str  #"user" or "assistant"
    content: str  #The main message content or user query"
    created_at: datetime 
    content_type: str  #This will be used what different types of content are there(text,image,table)
    metadata: Dict[str, Any]  #Additional information about the message(Here we need to add any image url's and code blocks)
    
class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    code: str
    code_explanation: str

class MessageFeedback(BaseModel):
    """Message feedback model"""
    message_id: str
    session_id: str
    feedback: str #"thumbs up" or "thumbs down"
    created_at: datetime

class SmartQuestions(BaseModel):
    """Let the Model suggest some smart questions which the user may want to ask"""
    questions_list: List[str]
