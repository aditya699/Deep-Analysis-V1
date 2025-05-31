'''
Note: Here we will having all the utilities for the container , which is a sandbox environment for the agents to run there code 
'''
import asyncio
from app.llm.openai_client import get_openai_client
from app.db.mongo import log_error
from app.container.schemas import ContainerSchema
from datetime import datetime
from app.db.mongo import get_db
import requests
import os
from app.core.config import settings
import uuid
import aiohttp
import aiofiles
import tempfile

async def create_new_container():
    """
    This function is used to create a new container
    """
    try:
        client = await get_openai_client()
        # Generate a unique name for the container
        container_name = f"container-{uuid.uuid4().hex[:8]}"
        container = await client.containers.create(name=container_name)
        container_id = container.id
        return container_id
    except Exception as e:
        await log_error(e, "container/utils.py", "create_new_container")
        raise e

async def get_all_active_containers():
    """
    This function is used to get all the containers from the openai client
    """
    try:
        client = await get_openai_client()
        db = await get_db()
        print(f"Database connection established: {db.name}")
        
        # For async client, we need to iterate through the paginator
        containers_paginator = client.containers.list()
        containers_list = []
        
        # Collect all containers from the paginator
        async for container in containers_paginator:
            containers_list.append(container)
        
        print(f"Containers: {containers_list}")
        
        # Find first active (running) container
        active_container = None
        for container in containers_list:
            print(f"Container {container.id}: {container.status}")
            if container.status == "running":
                active_container = container
                break
                
        if active_container is None:
            # Create a new container
            container_id = await create_new_container()
            print(f"Created new container with ID: {container_id}")
            
            # Create container document
            container_doc = ContainerSchema(container_id=container_id, created_at=datetime.now()).model_dump()
            print(f"Container document to insert: {container_doc}")
            
            # Insert into database
            result = await db["containers"].insert_one(container_doc)
            print(f"Database insert result: {result.inserted_id}")
            
            return container_id
        else:
            print(f"Using existing container: {active_container.id}")
            # Create container document for existing container
            container_doc = ContainerSchema(container_id=active_container.id, created_at=datetime.now()).model_dump()
            print(f"Container document to insert: {container_doc}")
            
            # Insert into database
            result = await db["containers"].insert_one(container_doc)
            print(f"Database insert result: {result.inserted_id}")
            
            return active_container.id
    except Exception as e:
        print(f"Error in get_all_active_containers: {str(e)}")
        print(f"Error type: {type(e)}")
        await log_error(e, "container/utils.py", "get_all_active_containers")
        raise e
 
async def upload_file_to_container(container_id: str, file_url: str) -> str:
    """
    Upload file to OpenAI container with streaming (8KB memory max)
    
    Args:
        container_id: OpenAI container ID  
        file_url: Azure blob URL
        
    Returns:
        str: File path in container
    """
    temp_file_path = None
    
    try:
        # Create temp file
        temp_fd, temp_file_path = tempfile.mkstemp(suffix='.csv')
        os.close(temp_fd)
        
        # Stream Azure → Disk
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                response.raise_for_status()
                async with aiofiles.open(temp_file_path, 'wb') as temp_file:
                    async for chunk in response.content.iter_chunked(8192):
                        await temp_file.write(chunk)
        
        # Stream Disk → OpenAI  
        filename = file_url.split('/')[-1]
        headers = {"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"}
        url = f"https://api.openai.com/v1/containers/{container_id}/files"
        
        async with aiohttp.ClientSession() as session:
            async with aiofiles.open(temp_file_path, 'rb') as fp:
                form = aiohttp.FormData()
                form.add_field("file", fp, filename=filename)
                
                async with session.post(url, headers=headers, data=form) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return result['path']
    
    finally:
        # Cleanup
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
    
#NOTE: This is just testing code
if __name__ == "__main__":
    # Example usage when running the file directly
    async def main():
        try:
            container = await get_all_active_containers()
            if container:
                print(f"Found active container or created new container: {container}")
            else:
                print("No active containers found")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    asyncio.run(main())