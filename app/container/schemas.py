from pydantic import BaseModel
from datetime import datetime

#Keeping containers seperate from any other logic since these die in 20 minutes if not used
class Container(BaseModel):
    """
    Container schema for the container
    """
    container_id: str
    created_at: datetime


  
    
