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
from app.container.utils import get_all_active_containers
import base64
from azure.storage.blob import BlobBlock

router = APIRouter()

# BUG:  file_content = await file.read()(This operation can choke the server if multiple requests are made simultaneously we need to chunk it)

@router.post("/upload_csv", response_model=UploadCSVResponse)
async def upload_csv_true_streaming(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    TRUE STREAMING: Never store the full file in memory!
    Stream directly to Azure while getting CSV preview from first chunk.
    """
    
    # 1. Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are allowed"
        )
    
    # 2. TRUE STREAMING SETUP
    max_size = 30 * 1024 * 1024  # 30MB in bytes
    chunk_size = 64 * 1024  # 64KB chunks
    azure_block_size = 4 * 1024 * 1024  # 4MB Azure blocks
    
    total_size = 0
    csv_preview_data = None
    column_names = None
    total_columns = 0
    
    # Azure setup
    session_id = str(uuid.uuid4())
    blob_service_client = BlobServiceClient.from_connection_string(settings.BLOB_STORAGE_ACCOUNT_KEY)
    container_name = "images-analysis"
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    blob_name = f"{session_id}_{timestamp}_{file.filename}"
    blob_client = blob_service_client.get_container_client(container_name).get_blob_client(blob_name)
    
    # Azure block upload setup
    
    block_list = []
    current_block_data = bytearray()
    block_counter = 0
    
    print("🚀 TRUE STREAMING: Processing file without storing full content...")
    
    try:
        # Create container if needed
        try:
            blob_service_client.get_container_client(container_name).create_container()
        except:
            pass
        
        # TRUE STREAMING LOOP
        while True:
            # Read one chunk at a time
            chunk = await file.read(chunk_size)
            if not chunk:
                break  # End of file
            
            total_size += len(chunk)
            print(f"📥 Processing chunk: {len(chunk)} bytes (Total processed: {total_size} bytes)")
            
            # Size check - early exit if too big
            if total_size > max_size:
                print("❌ File too large - stopping stream")
                raise HTTPException(
                    status_code=400,
                    detail=f"File too large. Maximum size is {max_size//1024//1024}MB"
                )
            
            # GET CSV PREVIEW FROM FIRST CHUNK ONLY
            if csv_preview_data is None and total_size <= chunk_size:
                try:
                    # Decode first chunk to get CSV structure
                    csv_string = chunk.decode('utf-8')
                    df = pd.read_csv(StringIO(csv_string), nrows=5)
                    
                    if df.empty or len(df.columns) == 0:
                        raise HTTPException(status_code=400, detail="Invalid CSV format")
                    
                    # Extract metadata from first chunk
                    total_columns = len(df.columns)
                    column_names = df.columns.tolist()
                    
                    # Create preview data
                    csv_preview_data = []
                    for index, row in df.iterrows():
                        row_dict = {}
                        for column in df.columns:
                            value = row[column]
                            if pd.isna(value):
                                row_dict[column] = None
                            elif isinstance(value, (int, float)):
                                row_dict[column] = value.item() if hasattr(value, 'item') else value
                            else:
                                row_dict[column] = str(value)
                        csv_preview_data.append(row_dict)
                    
                    print(f"✅ CSV preview extracted from first chunk: {total_columns} columns")
                    del df, csv_string  # Free memory immediately
                    
                except Exception as e:
                    print(f"❌ Error processing CSV preview: {e}")
                    raise HTTPException(status_code=400, detail="Invalid CSV format")
            
            # ADD CHUNK TO CURRENT AZURE BLOCK
            current_block_data.extend(chunk)
            
            # UPLOAD BLOCK WHEN IT REACHES 4MB OR END OF FILE
            if len(current_block_data) >= azure_block_size:
                # Upload this block to Azure immediately
                block_id = base64.b64encode(f"block-{block_counter:06d}".encode()).decode()
                
                print(f"📤 Uploading Azure block {block_counter + 1}: {len(current_block_data)} bytes")
                
                blob_client.stage_block(
                    block_id=block_id,
                    data=bytes(current_block_data)
                )
                
                block_list.append(BlobBlock(block_id=block_id))
                block_counter += 1
                
                print(f"✅ Block uploaded. Memory freed. Total blocks: {len(block_list)}")
                
                # CLEAR BLOCK DATA - FREE MEMORY!
                current_block_data = bytearray()
        
        # Upload final block if there's remaining data
        if len(current_block_data) > 0:
            block_id = base64.b64encode(f"block-{block_counter:06d}".encode()).decode()
            
            print(f"📤 Uploading final Azure block: {len(current_block_data)} bytes")
            
            blob_client.stage_block(
                block_id=block_id,
                data=bytes(current_block_data)
            )
            
            block_list.append(BlobBlock(block_id=block_id))
            print(f"✅ Final block uploaded")
        
        # Commit all blocks to create final blob
        print(f"🔗 Committing {len(block_list)} blocks to create final blob...")
        
        blob_client.commit_block_list(
            block_list=block_list,
            content_type="text/csv"
        )
        
        file_url = blob_client.url
        
        print(f"✅ TRUE STREAMING COMPLETE!")
        print(f"📊 Total file size: {total_size} bytes")
        print(f"📊 Azure blocks created: {len(block_list)}")
        print(f"💾 Max memory used: ~{azure_block_size//1024//1024}MB (one block)")
        print(f"🔗 File URL: {file_url}")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error during streaming: {e}")
        raise HTTPException(status_code=500, detail="Error during file processing")
    
    # Validate that we got CSV preview
    if csv_preview_data is None:
        raise HTTPException(status_code=400, detail="Could not extract CSV preview")
    
    # 3. Save session data to MongoDB
    try:
        session_document = {
            "session_id": session_id,
            "user_email": current_user["email"],
            "user_id": str(current_user["_id"]),
            "file_info": {
                "original_filename": file.filename,
                "blob_name": blob_name,
                "container_name": container_name,
                "file_url": file_url,
                "file_size": total_size,
                "content_type": "text/csv"
            },
            "csv_info": {
                "total_columns": total_columns,
                "column_names": column_names,
                "preview_data": csv_preview_data
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "status": "active"
        }
        
        sessions_collection = db["csv_sessions"]
        result = await sessions_collection.insert_one(session_document)
        
        if not result.inserted_id:
            raise Exception("Failed to create session in database")
        
        print(f"✅ MongoDB session created: {session_id}")
        
    except Exception as e:
        # Clean up blob if database fails
        try:
            blob_client.delete_blob()
            print(f"🗑️ Cleaned up blob after database error")
        except:
            pass
        
        await log_error(
            error=e,
            location="upload_csv_mongodb",
            additional_info={"session_id": session_id, "user_email": current_user["email"]}
        )
        raise HTTPException(status_code=500, detail="Failed to create session in database")
    
    # 4. Return response
    return {
        "session_id": session_id,
        "file_url": file_url,
        "file_name": file.filename,
        "preview_data": csv_preview_data,
        "file_info": {
            "original_filename": file.filename,
            "blob_name": blob_name,
            "container_name": container_name,
            "file_url": file_url,
            "file_size": total_size,
            "content_type": "text/csv"
        },
        "message": "CSV file uploaded successfully with true streaming",
        "success": True
    }
    

@router.post("/chat")
async def chat_response(
    session_id: str,
    user_query: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
    container_id: str = Depends(get_all_active_containers)
):
    """
    This endpoint is used to get the chat response for the user query
    """
    try:
        #Get the session from the database
        session = await db["csv_sessions"].find_one({"session_id": session_id})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        #From the session get the file_url
        file_url = session["file_info"]["file_url"]

        #Post file_url upload the file to the container
        pass
    except Exception as e:
        pass


