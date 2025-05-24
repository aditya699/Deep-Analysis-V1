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
from azure.storage.blob import BlobServiceClient
from app.core.config import settings
from app.db.mongo import log_error
from app.chat.schemas import UploadCSVResponse

router = APIRouter()

@router.post("/upload_csv", response_model=UploadCSVResponse)
async def upload_csv(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Upload a CSV file and start a chat session.
    Returns session_id, file_url, file_name, and preview_data.
    """
    
    # 1. Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are allowed"
        )
    
    # 2. Validate file size (max 30MB)
    max_size = 30 * 1024 * 1024  # 30MB in bytes
    file_content = await file.read()
    
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=400,
            detail="File size too large. Maximum size is 50MB"
        )
    
    # Store the original file content for blob upload
    original_file_content = file_content
    
    # 3. Read and validate CSV content (memory optimized)
    try:
        # Convert bytes to string
        csv_string = file_content.decode('utf-8')
        
        # Read only first 5 rows for preview
        # NOTE :This will read 5 rows if 5 rows are present, if less than 5 rows are present then it will read all the rows
        df = pd.read_csv(StringIO(csv_string), nrows=5)
        
        # Basic validation
        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="CSV file is empty"
            )
            
        if len(df.columns) == 0:
            raise HTTPException(
                status_code=400,
                detail="CSV file has no columns"
            )
        
        # Extract metadata from the sample
        total_columns = len(df.columns)
        column_names = df.columns.tolist()
        
        # Create preview data
        preview_data = []
        for index, row in df.iterrows():
            row_dict = {}
            for column in df.columns:
                # Handle NaN values and convert to appropriate types
                value = row[column]
                if pd.isna(value):
                    row_dict[column] = None
                elif isinstance(value, (int, float)):
                    # Keep numeric values as-is, but convert numpy types to Python types
                    row_dict[column] = value.item() if hasattr(value, 'item') else value
                else:
                    # Convert everything else to string
                    row_dict[column] = str(value)
            preview_data.append(row_dict)
        
        # Clean up immediately
        del df
        del csv_string
            
    except UnicodeDecodeError as e:
        await log_error(
            error=e,
            location="upload_csv_file_validation",
            additional_info={"filename": file.filename, "user_email": current_user["email"]}
        )
        raise HTTPException(
            status_code=400,
            detail="Invalid file encoding. Please ensure the file is UTF-8 encoded"
        )
    except pd.errors.EmptyDataError as e:
        await log_error(
            error=e,
            location="upload_csv_file_validation",
            additional_info={"filename": file.filename, "user_email": current_user["email"]}
        )
        raise HTTPException(
            status_code=400,
            detail="CSV file is empty or invalid"
        )
    except Exception as e:
        await log_error(
            error=e,
            location="upload_csv_file_validation",
            additional_info={"filename": file.filename, "user_email": current_user["email"]}
        )
        raise HTTPException(
            status_code=400,
            detail="Error reading CSV file"
        )
    
    # 4. Generate session ID
    session_id = str(uuid.uuid4())
    
    # 5. Prepare file metadata (without total_rows)
    file_metadata = {
        "session_id": session_id,
        "original_filename": file.filename,
        "file_size": len(file_content),
        "total_columns": total_columns,
        "column_names": column_names,
        "upload_timestamp": datetime.utcnow(),
        "user_email": current_user["email"]
    }
    
    # 6. Upload file to Azure Blob Storage
    try:
        # Initialize Azure Blob Service Client
        blob_service_client = BlobServiceClient.from_connection_string(
            settings.BLOB_STORAGE_ACCOUNT_KEY
        )
        
        # Define container and blob names
        container_name = "images-analysis"  
        
        # Create a unique blob name using session_id and original filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        blob_name = f"{session_id}_{timestamp}_{file.filename}"
        
        # Get container client
        container_client = blob_service_client.get_container_client(container_name)
        
        # Create container if it doesn't exist
        try:
            container_client.create_container()
        except Exception:
            # Container might already exist, which is fine
            pass
        
        # Get blob client
        blob_client = container_client.get_blob_client(blob_name)
        
        # Upload the file to blob storage
        blob_client.upload_blob(
            data=original_file_content,
            overwrite=True,
            content_type="text/csv"
        )
        
        # Generate the blob URL
        file_url = blob_client.url
        
        # Update file metadata with storage information
        file_metadata.update({
            "blob_name": blob_name,
            "container_name": container_name,
            "file_url": file_url,
            "storage_status": "uploaded"
        })
        
    except AzureError as e:
        await log_error(
            error=e,
            location="upload_csv_blob_storage",
            additional_info={
                "session_id": session_id,
                "user_email": current_user["email"],
                "filename": file.filename
            }
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to upload file to storage"
        )
    except Exception as e:
        await log_error(
            error=e,
            location="upload_csv_blob_storage",
            additional_info={
                "session_id": session_id,
                "user_email": current_user["email"],
                "filename": file.filename
            }
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to upload file to storage"
        )
    
    # 7. Save session data to MongoDB
    try:
        # Prepare session document for MongoDB (without total_rows)
        session_document = {
            "session_id": session_id,
            "user_email": current_user["email"],
            "user_id": str(current_user["_id"]),  # Convert ObjectId to string
            # File information
            "file_info": {
                "original_filename": file.filename,
                "blob_name": file_metadata["blob_name"],
                "container_name": file_metadata["container_name"],
                "file_url": file_url,
                "file_size": file_metadata["file_size"],
                "content_type": "text/csv"
            },
            
            # CSV structure information
            "csv_info": {
                "total_columns": file_metadata["total_columns"],
                "column_names": file_metadata["column_names"],
                "preview_data": preview_data
            },
            
            # Session metadata
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "status": "active"
        }
        
        # Insert session into MongoDB
        sessions_collection = db["csv_sessions"]
        result = await sessions_collection.insert_one(session_document)
        
        if not result.inserted_id:
            raise Exception("Failed to create session in database")
        
        # Log successful upload
        print(f"CSV session created successfully: {session_id} for user: {current_user['email']}")
        
    except Exception as e:
        # If MongoDB save fails, clean up the blob storage
        try:
            blob_client = blob_service_client.get_container_client(container_name).get_blob_client(blob_name)
            blob_client.delete_blob()
            print(f"Cleaned up blob after database error: {blob_name}")
        except:
            # If cleanup fails, just log it but don't raise another exception
            pass
        
        # Log the database error
        await log_error(
            error=e,
            location="upload_csv_mongodb",
            additional_info={
                "session_id": session_id,
                "user_email": current_user["email"],
                "blob_name": blob_name
            }
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to create session in database"
        )
    
    # 8. Return the final API response
    try:
        # Construct the success response (without total_rows)
        response_data = {
            "session_id": session_id,
            "file_url": file_url,
            "file_name": file.filename,
            "preview_data": preview_data,
            "file_info": {
                "original_filename": file.filename,
                "blob_name": file_metadata["blob_name"],
                "container_name": file_metadata["container_name"],
                "file_url": file_url,
                "file_size": file_metadata["file_size"],
                "content_type": "text/csv"
            },
            "message": "CSV file uploaded successfully",
            "success": True
        }
        
        return response_data
        
    except Exception as e:
        await log_error(
            error=e,
            location="upload_csv_response",
            additional_info={
                "session_id": session_id,
                "user_email": current_user["email"]
            }
        )
        raise HTTPException(
            status_code=500,
            detail="Error creating response"
        )