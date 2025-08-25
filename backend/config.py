import os
from functools import lru_cache
from typing import Optional
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration settings.
    
    This class defines all the settings your app needs to run.
    It automatically reads values from environment variables or .env file.
    
    Field(...) means the field is REQUIRED - app won't start without it
    Field(default=value) means optional with a default value
    """
    
    # Tell Pydantic to read from .env file automatically
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    # Application settings - basic app info
    app_name: str = "Mental Health Services Chatbot API"  # App display name
    debug: bool = False  # Enable debug mode (more detailed errors)
    environment: str = Field(default="development", description="Environment: development, staging, production")
    
    # Database connection - REQUIRED, no default for security
    # Example: "postgresql://username:password@localhost:5432/database_name"
    database_url: str = Field(..., description="Database connection URL")
    
    # Security settings - for JWT token creation
    # The "..." means this field is REQUIRED - app won't start without it
    secret_key: str = Field(..., min_length=32, description="Secret key for JWT tokens")
    algorithm: str = "HS256"  # Encryption algorithm for JWT tokens
    access_token_expire_minutes: int = 30  # How long login tokens last
    
    # CORS (Cross-Origin Resource Sharing) - which websites can call your API
    # Default allows your frontend at localhost:3000 to access the API
    cors_origins: list[str] = Field(default=["http://localhost:3000"], description="Allowed CORS origins")
    
    # AI/LangGraph settings - REQUIRED for chatbot functionality
    openai_api_key: str = Field(..., description="OpenAI API key")  # Required for AI responses
    langsmith_api_key: Optional[str] = Field(default=None, description="LangSmith API key for tracing")  # Optional monitoring
    
    # External service APIs - Optional third-party integrations
    google_maps_api_key: Optional[str] = Field(default=None, description="Google Maps API key")  # For location services
    
    # Logging configuration
    log_level: str = Field(default="INFO", description="Log level")  # How detailed should logs be
    
    # VALIDATION FUNCTIONS - These run when the app starts to check your settings
    
    @validator("secret_key")
    def validate_secret_key(cls, v):
        """
        Ensures the secret key is secure.
        Prevents common weak keys that would make your app vulnerable.
        """
        if v in ["your-secret-key-here", "change-me", ""] or len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters and not use default values")
        return v
    
    @validator("environment")
    def validate_environment(cls, v):
        """
        Ensures environment is one of the allowed values.
        This helps prevent typos in deployment settings.
        """
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v
    
    @validator("database_url")
    def validate_database_url(cls, v):
        """
        Prevents using placeholder database URLs in production.
        Forces you to provide real database connection details.
        """
        if "user:password@localhost" in v or "change-me" in v:
            raise ValueError("Database URL must not contain placeholder values")
        return v


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