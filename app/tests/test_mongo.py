'''
NOTE:
1.This is a test file for the mongo.py file.
'''

import pytest
from app.db.mongo import get_client, get_db
from pymongo import AsyncMongoClient

@pytest.mark.asyncio
async def test_get_client_returns_instance():
    client = await get_client()
    assert isinstance(client, AsyncMongoClient)

@pytest.mark.asyncio
async def test_get_db_returns_database():
    db = await get_db()
    assert db.name == "deep_analysis"
