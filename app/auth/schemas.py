from pydantic import BaseModel, EmailStr

class EmailRequest(BaseModel):
    """
    Request to request password , this is for main login.
    """
    email: EmailStr

