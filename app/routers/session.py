from fastapi import APIRouter, Depends, HTTPException, status
import logging
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, DisconnectionError

from app.models.cdr import SessionInfo, SessionListResponse, SessionCreateRequest, SessionCreateResponse
from app.services.session_manager import get_session_manager
from app.database import get_db, handle_db_connection

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/sessions", response_model=SessionCreateResponse)
async def create_session(
    request: SessionCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Endpoint untuk membuat session baru
    """
    try:
        # Buat session baru
        session_manager = get_session_manager()
        session = session_manager.create_session(db, request.name, request.description)
        
        logger.info(f"Session baru dibuat: {session.id}")
        return SessionCreateResponse(
            success=True,
            message="Session berhasil dibuat",
            session_id=session.id
        )
    except (OperationalError, DisconnectionError) as e:
        logger.error(f"Koneksi database error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Layanan database tidak tersedia. Silakan coba lagi nanti."
        )
    except Exception as e:
        logger.error(f"Error membuat session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    db: Session = Depends(get_db)
):
    """
    Endpoint untuk mendapatkan daftar semua session
    """
    try:
        # Dapatkan semua session
        session_manager = get_session_manager()
        db_sessions = session_manager.get_all_sessions(db)
        
        # Konversi ke model SessionInfo
        sessions = [
            SessionInfo(
                session_id=session.id,
                created_at=session.created_at,
                record_count=session.record_count,
                description=session.description
            )
            for session in db_sessions
        ]
        
        return SessionListResponse(sessions=sessions)
    except (OperationalError, DisconnectionError) as e:
        logger.error(f"Koneksi database error saat mengambil daftar session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Layanan database tidak tersedia. Silakan coba lagi nanti."
        )
    except Exception as e:
        logger.error(f"Error mendapatkan daftar session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint untuk mendapatkan informasi session berdasarkan ID
    """
    try:
        # Dapatkan session
        session_manager = get_session_manager()
        session = session_manager.get_session(db, session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session dengan ID {session_id} tidak ditemukan"
            )
        
        # Konversi ke model SessionInfo
        return SessionInfo(
            session_id=session.id,
            created_at=session.created_at,
            record_count=session.record_count,
            description=session.description
        )
    except (OperationalError, DisconnectionError) as e:
        logger.error(f"Koneksi database error saat mengambil session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Layanan database tidak tersedia. Silakan coba lagi nanti."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error mendapatkan session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint untuk menghapus session berdasarkan ID
    """
    try:
        # Dapatkan session
        session_manager = get_session_manager()
        session = session_manager.get_session(db, session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session dengan ID {session_id} tidak ditemukan"
            )
        
        # Hapus session
        session_manager.delete_session(db, session_id)
        
        logger.info(f"Session {session_id} berhasil dihapus")
        return None
    except (OperationalError, DisconnectionError) as e:
        logger.error(f"Koneksi database error saat menghapus session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Layanan database tidak tersedia. Silakan coba lagi nanti."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error menghapus session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 