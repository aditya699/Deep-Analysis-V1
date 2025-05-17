from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    # Existing settings
    MONGO_URI: str
    OPENAI_API_KEY: str
    BLOB_STORAGE_ACCOUNT_KEY: str
    
    # Email settings
    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_USERNAME: str = ""
    EMAIL_PASSWORD: str = ""
    EMAIL_FROM: str = ""
    
    model_config = SettingsConfigDict(env_file=Path(__file__).parent.parent.parent / ".env")

settings = Settings()