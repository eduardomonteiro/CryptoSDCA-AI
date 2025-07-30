"""
src/core/config.py - Configuration management
"""

from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Application settings"""
    
    DATABASE_URL: str = Field(default="sqlite:///./data/cryptosdca.sqlite3")
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production")
    DEBUG: bool = Field(default=True)
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
