from pydantic import BaseModel


class GetAllSessions(BaseModel):
    """Get all sessions"""
    email: str
