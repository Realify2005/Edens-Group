import os
from functools import lru_cache
from typing import Optional
from pathlib import Path
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# point to backend/.env no matter where you run python from
BASE_DIR = Path(__file__).resolve().parent     # this = backend/
ENV_PATH = BASE_DIR / ".env"

class Settings(BaseSettings):
    """
    Application configuration settings.
    
    This class defines all the settings your app needs to run.
    It automatically reads values from environment variables or .env file.
    
    Field(...) means the field is REQUIRED - app won't start without it
    Field(default=value) means optional with a default value
    """
    
    # Tell Pydantic to read from .env file automatically
    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8"
    )

    # Application settings - basic app info
    app_name: str = "Mental Health Services Chatbot API"  # App display name
    debug: bool = False  # Enable debug mode (more detailed errors)
    environment: str = Field(default="development", description="Environment: development, staging, production")
    
    # Database connection - REQUIRED, no default for security
    # Example: "postgresql://username:password@localhost:5432/database_name"
    local_postgresql_database_url: str = Field(..., description="Local PostgreSQL database URL")
    heroku_postgresql_database_url: str = Field(..., description="Heroku PostgreSQL database URL")

    # Security settings - for JWT token creation
    # The "..." means this field is REQUIRED - app won't start without it
    # secret_key: str = Field(..., min_length=32, description="Secret key for JWT tokens")
    # algorithm: str = "HS256"  # Encryption algorithm for JWT tokens
    access_token_expire_minutes: int = 30  # How long login tokens last
    
    # CORS (Cross-Origin Resource Sharing) - which websites can call your API
    # Default allows your frontend at localhost:3000 to access the API
    cors_origins: list[str] = Field(default=["http://localhost:3000"], description="Allowed CORS origins")
    
    # AI/LangGraph settings - REQUIRED for chatbot functionality
    # openai_api_key: str = Field(..., description="OpenAI API key")  # Required for AI responses
    # langsmith_api_key: Optional[str] = Field(default=None, description="LangSmith API key for tracing")  # Optional monitoring
    
    # External service APIs - Optional third-party integrations
    geocode_provider: str = Field(default="mapbox", description="Geocode provider, e.g., mapbox")  # Which geocode service to use
    geocode_api_key: str = Field(..., description="Geocode API key")  # Required for geocoding
    
    # Logging configuration
    # log_level: str = Field(default="INFO", description="Log level")  # How detailed should logs be


@lru_cache()
def get_settings():
    """
    Returns the application settings.
    
    @lru_cache() means this function only runs once - the settings are cached
    in memory after the first call, making subsequent calls faster.
    
    Usage in your code:
        from config import get_settings
        settings = get_settings()
        print(settings.app_name)
    """
    return Settings()