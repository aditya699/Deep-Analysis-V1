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

    # JWT settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_SECONDS: int = 3600  # 1 hour
    REFRESH_TOKEN_EXPIRY_SECONDS: int = 259200  # 3 days
    
    model_config = SettingsConfigDict(env_file=Path(__file__).parent.parent.parent / ".env")

settings = Settings()