from fastapi import Request, HTTPException, status, Depends
from fastapi.security import APIKeyHeader
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Definisikan header API key
api_key_header = APIKeyHeader(name=settings.API_KEY_NAME, auto_error=False)

async def verify_api_key(request: Request, api_key: str = Depends(api_key_header)):
    """
    Middleware untuk memverifikasi API key
    """
    # Jika API key tidak ada di header
    if api_key is None:
        logger.warning(f"API key tidak ditemukan dalam request dari {request.client.host}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key diperlukan",
        )
    
    # Jika API key tidak valid
    if api_key != settings.API_KEY:
        logger.warning(f"API key tidak valid dari {request.client.host}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key tidak valid",
        )
    
    # API key valid
    return api_key 