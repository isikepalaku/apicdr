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
    Processes CDR files in different formats and extracts relevant information
    """
    
    @staticmethod
    def _detect_file_format(df: pd.DataFrame) -> str:
        """
        Detects the CDR file format based on columns
        Returns: 'standard' or 'detailed'
        """
        columns = set(col.lower() for col in df.columns)
        if 'a number' in columns and 'calltype' in columns:
            return 'detailed'
        return 'standard'

    @staticmethod
    def _filter_invalid_bnumbers(df: pd.DataFrame) -> pd.DataFrame:
        """
        Removes records with invalid B numbers
        """
        invalid_numbers = ['0', '8331', '100', '363', '8999']
        return df[~df['bnumber'].astype(str).isin(invalid_numbers)]

    @staticmethod
    def _standardize_detailed_format(df: pd.DataFrame) -> pd.DataFrame:
        """
        Converts detailed CSV format to standard format
        """
        # Create mapping for columns
        df = df.rename(columns={
            '% a number': 'anumber',
            '% b number': 'bnumber',
            '% c number': 'cnumber',
            '% calltype': 'call_type',
            '% duration': 'duration',
            '% date': 'date',
            '% time': 'time'
        })
        
        # Combine date and time
        df['date'] = pd.to_datetime(
            df['date'] + ' ' + df['time'],
            format='%d/%b/%y %H:%M:%S'
        )
        
        # Drop unused columns
        keep_columns = ['call_type', 'anumber', 'bnumber', 'date', 'duration']
        df = df[keep_columns]
        
        # Clean phone numbers
        df['anumber'] = df['anumber'].str.replace(r'^\+', '', regex=True)
        df['bnumber'] = df['bnumber'].str.replace(r'^\+', '', regex=True)

        # Filter out invalid B numbers
        df = CDRProcessor._filter_invalid_bnumbers(df)
        
        return df
    
    @staticmethod
    def process_cdr_file(file_content: bytes, session_id: str, db: Session) -> int:
        """
        Processes CDR file and adds it to session
        
        Args:
            file_content: CDR file content in bytes
            session_id: Session ID to store data
            db: Database session
            
        Returns:
            Number of records processed
        """
        try:
            # Try pipe-separated first, then comma-separated
            try:
                df = pd.read_csv(io.BytesIO(file_content), sep='|')
            except:
                df = pd.read_csv(io.BytesIO(file_content))
            
            # Standardize column names
            df.columns = [col.lower().strip('% ') for col in df.columns]
            
            # Detect and process format
            file_format = CDRProcessor._detect_file_format(df)
            if file_format == 'detailed':
                df = CDRProcessor._standardize_detailed_format(df)
            
            # Verify required columns
            required_columns = ['call_type', 'anumber', 'bnumber', 'date', 'duration']
            for col in required_columns:
                if col not in df.columns:
                    raise ValueError(f"Required column {col} not found in CDR file")
            
            # Handle different date formats
            if isinstance(df['date'].iloc[0], str):
                df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d %H:%M:%S.%f', errors='coerce')
            
            # Convert duration to integer, handle colon format
            df['duration'] = df['duration'].astype(str).str.replace(':', '')
            df['duration'] = pd.to_numeric(df['duration'], errors='coerce').fillna(0).astype(int)

            # Filter out invalid B numbers for both formats
            df = CDRProcessor._filter_invalid_bnumbers(df)
            
            # Add data to session
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