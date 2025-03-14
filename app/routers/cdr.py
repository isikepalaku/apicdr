from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
import logging
from typing import List, Optional
import json
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, DisconnectionError

from app.models.cdr import CDRUploadResponse, CDRAnalysisRequest, GraphData
from app.services.session_manager import get_session_manager
from app.services.cdr_processor import CDRProcessor
from app.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/cdr/upload", response_model=CDRUploadResponse)
async def upload_cdr_file(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Endpoint untuk mengunggah file CDR
    """
    try:
        # Dapatkan session manager
        session_manager = get_session_manager()
        
        # Cek apakah session ada
        if not session_manager.session_exists(session_id, db):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session dengan ID {session_id} tidak ditemukan"
            )
        
        # Baca file
        file_content = await file.read()
        
        # Proses file CDR menggunakan metode statis
        record_count = CDRProcessor.process_cdr_file(file_content, session_id, db)
        
        logger.info(f"File CDR berhasil diunggah untuk session {session_id}")
        return CDRUploadResponse(
            success=True,
            message="File CDR berhasil diunggah",
            records_processed=record_count,
            session_id=session_id
        )
    except (OperationalError, DisconnectionError) as e:
        logger.error(f"Koneksi database error saat mengunggah file CDR: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Layanan database tidak tersedia. Silakan coba lagi nanti."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error mengunggah file CDR: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/cdr/upload-multiple", response_model=CDRUploadResponse)
async def upload_multiple_cdr_files(
    files: List[UploadFile] = File(...),
    session_id: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Endpoint untuk mengunggah beberapa file CDR sekaligus
    """
    try:
        # Dapatkan session manager
        session_manager = get_session_manager()
        
        # Cek apakah session ada
        if not session_manager.session_exists(session_id, db):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session dengan ID {session_id} tidak ditemukan"
            )
        
        # Proses semua file CDR
        files_data = []
        total_records = 0
        
        for file in files:
            content = await file.read()
            files_data.append({
                "filename": file.filename,
                "content": content
            })
        
        # Proses file menggunakan metode statis
        total_records = CDRProcessor.process_multiple_cdr_files(files_data, session_id, db)
        
        logger.info(f"{len(files)} file CDR berhasil diunggah untuk session {session_id}")
        return CDRUploadResponse(
            success=True,
            message=f"{len(files)} file CDR berhasil diunggah",
            records_processed=total_records,
            session_id=session_id
        )
    except (OperationalError, DisconnectionError) as e:
        logger.error(f"Koneksi database error saat mengunggah multiple file CDR: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Layanan database tidak tersedia. Silakan coba lagi nanti."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error mengunggah file CDR: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/cdr/analyze", response_model=GraphData)
async def analyze_cdr(
    request: CDRAnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Endpoint untuk menganalisis data CDR dan membuat graph
    """
    try:
        # Dapatkan session manager
        session_manager = get_session_manager()
        
        # Cek apakah session ada
        if not session_manager.session_exists(request.session_id, db):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session dengan ID {request.session_id} tidak ditemukan"
            )
        
        # Dapatkan data graph
        graph_data = session_manager.get_graph_data(
            db, 
            request.session_id,
            filter_options=request.filter_options
        )
        
        logger.info(f"Analisis CDR berhasil untuk session {request.session_id}")
        return graph_data
    except (OperationalError, DisconnectionError) as e:
        logger.error(f"Koneksi database error saat menganalisis CDR: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Layanan database tidak tersedia. Silakan coba lagi nanti."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error menganalisis CDR: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 