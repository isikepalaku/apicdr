import pandas as pd
import io
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
from sqlalchemy.orm import Session
from app.services.session_manager import get_session_manager

logger = logging.getLogger(__name__)

class CDRProcessor:
    """
    Memproses file CDR dan mengekstrak informasi yang relevan
    """
    
    @staticmethod
    def process_cdr_file(file_content: bytes, session_id: str, db: Session) -> int:
        """
        Memproses file CDR dan menambahkannya ke session
        
        Args:
            file_content: Konten file CDR dalam bentuk bytes
            session_id: ID session untuk menyimpan data
            db: Database session
            
        Returns:
            Jumlah record yang berhasil diproses
        """
        try:
            # Baca file CSV
            df = pd.read_csv(io.BytesIO(file_content), sep='|')
            
            # Standarisasi nama kolom (lowercase)
            df.columns = [col.lower() for col in df.columns]
            
            # Pastikan kolom yang diperlukan ada
            required_columns = ['call_type', 'anumber', 'bnumber', 'date', 'duration']
            for col in required_columns:
                if col not in df.columns:
                    raise ValueError(f"Kolom {col} tidak ditemukan dalam file CDR")
            
            # Konversi kolom date ke datetime
            df['date'] = pd.to_datetime(df['date'])
            
            # Konversi kolom duration ke integer
            df['duration'] = pd.to_numeric(df['duration'], errors='coerce').fillna(0).astype(int)
            
            # Tambahkan data ke session
            session_manager = get_session_manager()
            record_count = session_manager.add_cdr_data(db, session_id, df)
            
            logger.info(f"Processed {record_count} CDR records for session {session_id}")
            return record_count
            
        except Exception as e:
            logger.error(f"Error processing CDR file: {str(e)}")
            raise
    
    @staticmethod
    def process_multiple_cdr_files(files: List[Dict[str, Any]], session_id: str, db: Session) -> int:
        """
        Memproses beberapa file CDR dan menambahkannya ke session
        
        Args:
            files: List file CDR (dict dengan keys 'filename' dan 'content')
            session_id: ID session untuk menyimpan data
            db: Database session
            
        Returns:
            Jumlah total record yang berhasil diproses
        """
        total_records = 0
        
        for file_info in files:
            file_content = file_info["content"]
            filename = file_info["filename"]
            
            try:
                record_count = CDRProcessor.process_cdr_file(file_content, session_id, db)
                total_records += record_count
                logger.info(f"Processed file {filename}: {record_count} records")
            except Exception as e:
                logger.error(f"Error processing file {filename}: {str(e)}")
                # Lanjutkan ke file berikutnya
        
        return total_records 