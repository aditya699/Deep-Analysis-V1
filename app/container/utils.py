'''
Note: Here we will having all the utilities for the container , which is a sandbox environment for the agents to run there code 
'''
import asyncio
from app.llm.openai_client import get_openai_client
from app.db.mongo import log_error
from app.container.schemas import Container
from datetime import datetime
from app.db.mongo import get_db

async def create_new_container():
    """
    This function is used to create a new container
    """
    try:
        client = await get_openai_client()
        container = client.containers.create()
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
        
        containers = client.containers.list()
        # Find first active (running) container
        active_container = None
        for container in containers.data:
                print(f"Container {container.id}: {container.status}")
                if container.status == "running":
                            active_container = container
                            break
                
        if active_container is None:
            # Create a new container
            container_id = await create_new_container()
            print(f"Created new container with ID: {container_id}")
            
            # Create container document
            container_doc = Container(container_id=container_id, created_at=datetime.now()).model_dump()
            print(f"Container document to insert: {container_doc}")
            
            # Insert into database
            result = await db["containers"].insert_one(container_doc)
            print(f"Database insert result: {result.inserted_id}")
            
            return container_id
        else:
            print(f"Using existing container: {active_container.id}")
            # Create container document for existing container
            container_doc = Container(container_id=active_container.id, created_at=datetime.now()).model_dump()
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

#NOTE: This is just a testing code
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
