import os
import aiohttp
import uuid
from datetime import datetime
from typing import Optional
from app.core.config import settings
from app.db.mongo import log_error
from azure.storage.blob.aio import BlobServiceClient

async def download_file_from_container(file_id: str,container_id: str, blob_service_client: BlobServiceClient) -> Optional[str]:
    """
    Download a file from the container and upload it to Azure Blob Storage.
    
    Args:
        file_id (str): The ID of the file to download
        
    Returns:
        Optional[str]: The Azure Blob Storage URL if successful, None otherwise
    """
    try:
        # Construct the download URL
        download_url = f"https://api.openai.com/v1/containers/{container_id}/files/{file_id}/content"
        headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
        
        # Azure setup
        container_name = "images-analysis"
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        blob_name = f"{uuid.uuid4()}_{timestamp}.png"
        
        
        # Download from OpenAI and upload to Azure in one shot
        async with aiohttp.ClientSession() as session:
            #NOTE: This is not a good practice to download the file in one shot, we should download the file in chunks and upload it to Azure in chunks but since we are just having images which are 0.1 MB we can do this
            async with session.get(download_url, headers=headers) as response:
                if response.status == 200:
                    # Get blob client
                    blob_client_container = blob_service_client.get_container_client(container_name).get_blob_client(blob_name)
                    
                    # Get file content and upload in one shot
                    file_content = await response.read()
                    await blob_client_container.upload_blob(file_content, overwrite=True)
                    
                    # Return the blob URL
                    return blob_client_container.url
                else:
                    await log_error(
                        error=f"Failed to download file: {response.status}",
                        location="download_file_from_container",
                        additional_info={"file_id": file_id, "status_code": response.status}
                    )
                    return None
                    
    except Exception as e:
        await log_error(
            error=e,
            location="download_file_from_container",
            additional_info={"file_id": file_id}
        )
        return None
    
