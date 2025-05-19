from pydantic import BaseModel
from typing import List, Dict, Any

class FileInfo(BaseModel):
    """File metadata information"""
    total_columns: int
    file_size: int
    column_names: List[str]
    # Removed total_rows

class UploadCSVResponse(BaseModel):
    """Response model for CSV upload endpoint"""
    session_id: str
    file_url: str
    file_name: str
    preview_data: List[Dict[str, Any]]
    file_info: FileInfo
    message: str
    success: bool