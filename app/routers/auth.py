from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import APIKeyHeader
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, DisconnectionError
from typing import Optional

from app.models.auth import UserListResponse
from app.database import get_db
from app.models.database_models import User
from app.utils.api_key_auth import verify_api_key

router = APIRouter()
logger = logging.getLogger(__name__)

# Gunakan API key untuk autentikasi
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

@router.get("/auth/users", response_model=UserListResponse)
async def list_users(
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Endpoint untuk mendapatkan daftar semua user (diproteksi dengan API key)
    """
    try:
        # Dapatkan semua user
        users = db.query(User).all()
        
        return UserListResponse(users=users)
    except (OperationalError, DisconnectionError) as e:
        logger.error(f"Koneksi database error saat mengambil daftar user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Layanan database tidak tersedia. Silakan coba lagi nanti."
        )
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 