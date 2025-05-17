from pydantic import BaseModel, EmailStr
from datetime import datetime

class EmailRequest(BaseModel):
    """
    Request to request password, this is for main login.
    """
    email: EmailStr

class User(BaseModel):
    """
    User model for the database.
    """
    email: EmailStr
    password: str
    password_expiry: datetime  # New field for password expiration
    created_at: datetime
    updated_at: datetime
    no_of_csv_files_daily_limit: int = 1

class LoginResponse(BaseModel):
    """
    Response model for the login request endpoint.
    """
    message: str
    success: bool
    email: EmailStr