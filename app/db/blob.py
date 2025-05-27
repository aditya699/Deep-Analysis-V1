from azure.storage.blob.aio import BlobServiceClient
from app.core.config import settings
from app.db.mongo import log_error
from fastapi import HTTPException

blob_client = None

async def get_blob_client():
    try:
        global blob_client
        if blob_client is None:
            blob_client = BlobServiceClient.from_connection_string(settings.BLOB_STORAGE_ACCOUNT_KEY)
        return blob_client
    except Exception as e:
        await log_error(
            error=e,
            location="get_blob_client",
            additional_info={"action": "get_blob_client"}
        )
        return HTTPException(status_code=500, detail="Failed to get blob client")
