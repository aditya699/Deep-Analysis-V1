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
router = APIRouter()

@router.post("/upload_csv", response_model=UploadCSVResponse)
async def upload_csv_true_streaming(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
    blob_client: BlobServiceClient = Depends(get_blob_client)
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
    
    # 2. Content-Type header check (add this)
    if file.content_type != 'text/csv':
        raise HTTPException(status_code=400, detail="Invalid content type. Must be text/csv")
    
    # 2. TRUE STREAMING SETUP
    max_size = 30 * 1024 * 1024  # 30MB in bytes

    #NOTE : This is a security measure to prevent the user from uploading a file that is too large
    if file.size and file.size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {max_size//1024//1024}MB"
        )
    
    chunk_size = 64 * 1024  # 64KB chunks
    azure_block_size = 4 * 1024 * 1024  # 4MB Azure blocks
    
    total_size = 0
    csv_preview_data = None
    column_names = None
    total_columns = 0
    
    # Azure setup
    session_id = str(uuid.uuid4())
    blob_service_client = blob_client
    container_name = "images-analysis"
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    blob_name = f"{session_id}_{timestamp}_{file.filename}"
    blob_client_container = blob_service_client.get_container_client(container_name).get_blob_client(blob_name)
    
    # Azure block upload setup
    block_list = []
    current_block_data = bytearray()
    block_counter = 0
    
    print("🚀 TRUE STREAMING: Processing file without storing full content...")
    
    try:
        # Create container if needed
        try:
            await blob_service_client.get_container_client(container_name).create_container()
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
                
                await blob_client_container.stage_block(
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
            
            await blob_client_container.stage_block(
                block_id=block_id,
                data=bytes(current_block_data)
            )
            
            block_list.append(BlobBlock(block_id=block_id))
            print(f"✅ Final block uploaded")
        
        # Commit all blocks to create final blob
        print(f"🔗 Committing {len(block_list)} blocks to create final blob...")
        
        await blob_client_container.commit_block_list(
            block_list=block_list,
            content_type="text/csv"
        )
        
        file_url = blob_client_container.url
        
        print(f"✅ TRUE STREAMING COMPLETE!")
        print(f"📊 Total file size: {total_size} bytes")
        print(f"📊 Azure blocks created: {len(block_list)}")
        print(f"💾 Max memory used: ~{azure_block_size//1024//1024}MB (one block)")
        print(f"🔗 File URL: {file_url}")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error during streaming: {e}")
        raise HTTPException(status_code=500, detail="Something went wrong at our end. Don't worry, we will fix it asap.")
    
    # Validate that we got CSV preview
    if csv_preview_data is None:
        raise HTTPException(status_code=400, detail="Could not extract CSV preview")
    
    # Generate smart questions using OpenAI
    
    try:
        openai_client = await get_openai_client()
        
        # Create prompt for smart questions generation
        smart_questions_prompt = f"""
        Based on the following CSV file information, generate 5 smart, insightful questions that a business analyst might want to ask about this data:

        File name: {file.filename}
        Columns: {column_names}
        Sample data: {csv_preview_data}

        Generate questions that would help uncover business insights, trends, patterns, or actionable information from this dataset. 
        Make the questions specific to the data structure and content shown.
        """
        
        response = await openai_client.responses.parse(
            model="gpt-4.1-mini",
            input=[
                {"role": "system", "content": "Generate exactly 5 smart business questions about the CSV data based on the provided information."},
                {"role": "user", "content": smart_questions_prompt}
            ],
            text_format=SmartQuestions
        )
        
        smart_questions = response.output_parsed.questions_list
        print(f"✅ Generated {len(smart_questions)} smart questions")
        
    except Exception as e:
        print(f"⚠️ Error generating smart questions: {e}")
        smart_questions = []
    
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
            "smart_questions": smart_questions,
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
            await blob_client_container.delete_blob()
            print(f"🗑️ Cleaned up blob after database error")
        except:
            pass
        
        await log_error(
            error=e,
            location="upload_csv_mongodb",
            additional_info={"session_id": session_id, "user_email": current_user["email"]}
        )
        raise HTTPException(status_code=500, detail="Something went wrong at our end. Don't worry, we will fix it asap.")
    
    # 4. Return response with smart questions

    print(f"Smart questions: {smart_questions}")
    response_data = {
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
        "smart_questions": smart_questions,
        "message": "CSV file uploaded successfully with true streaming",
        "success": True
    }
    
    return response_data

@router.post("/chat")
async def chat_response(
    session_id: str,
    user_query: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
    container_id: str = Depends(get_all_active_containers),
    openai_client: OpenAI = Depends(get_openai_client),
    blob_client: BlobServiceClient = Depends(get_blob_client)
):
    """
    This endpoint is used to get the chat response for the user query
    """
    try:
        #Get the session from the database
        #Add a check to see if the session is owned by the user
        session = await db["csv_sessions"].find_one({"session_id": session_id, "user_email": current_user["email"]})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or not owned by the user")
        
        #Insert the user query into the database
        await db["messages"].insert_one({
            "session_id": session_id,
            "role": "user",
            "content": user_query,
            "created_at": datetime.utcnow(),
            "content_type": "text",
            "metadata": {}
        })
        
        #From the session get the file_url
        file_url = session["file_info"]["file_url"]

        #From the session get csv_info
        csv_info = session["csv_info"]

        #push the file to the container
        file_url = await upload_file_to_container(container_id, file_url)

        # Get message history for this session
        message_history = await db["messages"].find(
            {"session_id": session_id}
        ).sort("created_at", 1).to_list(length=None)

        # Format message history for the prompt
        conversation_history = ""
        for msg in message_history:
            role = msg["role"]
            content = msg["content"]
            conversation_history += f"{role}: {content}\n"

        #Create the prompt
        prompt = f"""
        You are a helpful assistant that answers questions about the uploaded CSV file.
        The file is located here: {file_url}
        The file has the following columns: {csv_info["column_names"]}
        Here is a preview of the data: {csv_info["preview_data"]}

        Previous conversation history:
        {conversation_history}

        Please answer the following user question. Respond directly if you can, and only use Python code or the code interpreter tool if it is necessary to answer the question accurately.

        Current User question: {user_query}
        """

        # Step 3: Analyze with code interpreter
        response = await openai_client.responses.create(
            model="gpt-4.1-mini",
            tools=[{"type": "code_interpreter", "container": container_id}],
            tool_choice="auto",
            input=prompt
        )
        print(response)

        # Initialize variables
        code_explain = None
        file_url = None
        code_content = None

        # Step 3.5 Handle charts generated and extract code
        for output in response.output:
            # Extract code if available
            if hasattr(output, 'code') and output.code:
                code_content = output.code

                #Step 4: Explain what the code is doing for observability
                code_explain=await openai_client.responses.create(
                                    model="gpt-4.1-mini",
                                    input=f"Explain what the following code is doing so that the business user can understand it. Format your explanation as a numbered list where each step starts with 'This code does:' followed by the action. For example: '1. This code does: Loads the data from the CSV file' : {code_content if code_content else None}.If no code is present, just say 'No code was generated'",
                                    instructions="You are a helpful assistant that can explain code to business users. You should explain the code in a way that is easy to understand."
                                )
            
            if hasattr(output, 'content'):
                for content in output.content:
                    if hasattr(content, 'annotations'):
                        for annotation in content.annotations:
                            if annotation.type == 'container_file_citation':
                                file_id = annotation.file_id
                                filename = annotation.filename
                                #Download the image file and upload it to the blob container
                                print("I Ran")
                                file_url = await download_file_from_container(file_id,container_id, blob_client)

                            
        
        if code_explain is None:
            code_explain_text = None
        else:
            code_explain_text = code_explain.output_text



        #Insert the assistant response into the database
        result= await db["messages"].insert_one({
            "session_id": session_id,
            "role": "assistant",
            "content": response.output_text,
            "created_at": datetime.utcnow(),
            "content_type": "text",
            "metadata": {"code": code_content, "code_explanation": code_explain_text, "file_url": file_url}
        })

        output_response={
            "response": response.output_text,
            "code": code_content,
            "code_explanation": code_explain_text,
            "file_url": file_url,
           "message_id": str(result.inserted_id) 
        }

        return output_response

    except Exception as e:
        await log_error(e, "chat/routes.py", "chat_response")
        raise HTTPException(status_code=500, detail="Something went wrong at our end. Don't worry, we will fix it asap.")

@router.post("/feedback")
async def submit_feedback(
    message_id: str,
    feedback: str,  # "thumbs_up" or "thumbs_down"
    db: Database = Depends(get_db)
):
    try:
        # Store feedback in MongoDB
        feedback_doc = {
            "message_id": message_id,
            "feedback": feedback,
            "created_at": datetime.utcnow()
        }
        
        await db["message_feedback"].insert_one(feedback_doc)
        
        return {"message": "Feedback submitted successfully", "success": True}
        
    except Exception as e:
        await log_error(error=e, location="submit_feedback")
        raise HTTPException(status_code=500, detail="Something went wrong at our end. Don't worry, we will fix it asap.")

@router.post("/chat_summary")
async def chat_summary(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    This endpoint generates a summary of the chat session, collects all generated images,
    and stores the summary in the database.
    """
    try:
        # Get the session from the database
        session = await db["csv_sessions"].find_one({"session_id": session_id})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get the message history for the session
        message_history = await db["messages"].find(
            {"session_id": session_id}
        ).sort("created_at", 1).to_list(length=None)

        # Collect all image URLs from the message history
        image_urls = []
        for message in message_history:
            if message.get("metadata") and message["metadata"].get("file_url"):
                image_urls.append(message["metadata"]["file_url"])

        # Create prompt for summary generation
        prompt = f"""
        You are a business analyst tasked with extracting key business insights from a chat conversation about data analysis.

        Please analyze the following chat history and provide a concise summary that focuses ONLY on:
        1. Key business insights discovered from the data
    
        Ignore technical details, casual conversation, and focus exclusively on business-relevant insights that would help stakeholders make informed decisions.

        Chat history:
        {message_history}

        Provide your response in a clear, executive-summary format with bullet points for easy reading.
        """

        # Get the openai client
        openai_client = await get_openai_client()

        # Get the chat summary using async response
        response = await openai_client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
            instructions="You are a helpful assistant that can summarize the chat history for the user. You should summarize the chat history in a way that is easy to understand."
        )

        # Create summary document for database
        summary_doc = {
            "session_id": session_id,
            "user_id": str(current_user["_id"]),
            "user_email": current_user["email"],
            "summary": response.output_text,
            "image_urls": image_urls,
            "created_at": datetime.utcnow()
        }

        # Store summary in database
        await db["chat_summaries"].insert_one(summary_doc)

        return {
            "summary": response.output_text,
            "image_urls": image_urls,
            "success": True
        }

    except Exception as e:
        await log_error(e, "chat/routes.py", "chat_summary")
        raise HTTPException(status_code=500, detail="Something went wrong at our end. Don't worry, we will fix it asap.")

        
        
        
        

