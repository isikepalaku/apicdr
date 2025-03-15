import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Konfigurasi umum
    APP_NAME: str = "CDR Analyzer API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Konfigurasi Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")
    
    # Konfigurasi PostgreSQL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Konfigurasi JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Konfigurasi API Key
    API_KEY: str = os.getenv("API_KEY", "cdr-analyzer-default-api-key")
    API_KEY_NAME: str = "X-API-Key"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Buat instance settings
settings = Settings() 