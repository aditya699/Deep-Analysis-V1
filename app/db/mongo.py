'''
NOTE:

1.This is a client for mongodb, which needs to be initialized once and reused.
2.Using PyMongo's native async client for MongoDB operations.
Refer:
https://pymongo.readthedocs.io/en/4.13.0/async-tutorial.html
'''
# db/mongo.py

from pymongo import AsyncMongoClient
from app.core.config import settings

#Initialize client and db (note:These will be initialized once and reused in all functions or routes)
client: AsyncMongoClient | None = None
db = None

async def get_client():
    global client
    if client is None:
        client = AsyncMongoClient(settings.MONGO_URI)
    return client

async def get_db():
    global db
    if db is None:
        client = await get_client()
        db = client["deep_analysis"]
    return db

    
