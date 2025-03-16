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
        # Convert columns to lowercase and remove % for comparison
        columns = set(col.lower().strip('% ') for col in df.columns)
        
        # Check for detailed format (A number, B number format)
        if any('a number' in col for col in columns) and any('b number' in col for col in columns):
            return 'detailed'
            
        # Check for standard format (simple column names)
        if all(col in columns for col in {'anumber', 'bnumber', 'date', 'duration'}):
            return 'standard'
            
        # Default to detailed if we have date and time columns
        if 'date' in columns and 'time' in columns:
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
        logger.info("Starting detailed format standardization")
        
        # Log original columns
        logger.debug(f"Original columns: {list(df.columns)}")
        
        # Log original columns for debugging
        logger.debug(f"Original columns before standardization: {list(df.columns)}")
        
        # Create comprehensive mapping for all possible columns
        logger.debug("Applying column mapping")
        column_mapping = {
            '% date': 'date',
            '% time': 'time',
            '% duration': 'duration',
            '% a number': 'anumber',
            '% a imei': 'imei',
            '% a imei type': 'imei_type',
            '% a imsi': 'imsi',
            '% a lac/cid': 'lac_ci',
            '% a sitename': 'sitename',
            '% b number': 'bnumber',
            '% b imei': 'b_imei',
            '% b imei type': 'b_imei_type',
            '% b imsi': 'b_imsi',
            '% b lac/cid': 'b_lac_ci',
            '% b sitename': 'b_sitename',
            '% calltype': 'call_type',
            '% direction': 'direction',
            '% c number': 'cnumber',
            '% a lat': 'latitude',
            '% a long': 'longitude',
            '% b lat': 'b_latitude',
            '% b long': 'b_longitude'
        }

        # Log original columns for debugging
        logger.debug(f"Original columns before mapping: {list(df.columns)}")
        
        # Rename columns but keep 'date' and 'time' as is for now
        df = df.rename(columns=column_mapping)
        
        # Handle duration - convert : to empty if present
        if 'duration' in df.columns:
            df['duration'] = df['duration'].replace(':', '0')
            df['duration'] = pd.to_numeric(df['duration'], errors='coerce').fillna(0).astype(int)
        
        # Handle date and time
        try:
            logger.error(f"Date values before parsing: {df['date'].head()}")
            logger.error(f"Time values before parsing: {df['time'].head()}")
            
            # Clean up date and time values
            df['date'] = df['date'].str.strip()
            df['time'] = df['time'].str.strip()
            # Parse date and time in dd/MMM/yy format
            df['date'] = pd.to_datetime(
                df['date'] + ' ' + df['time'],
                format='%d/%b/%y %H:%M:%S',
                errors='coerce'
            )
            
            # Drop the time column since it's now part of datetime
            df = df.drop('time', axis=1, errors='ignore')
            
            logger.error(f"Date values after parsing: {df['date'].head()}")
            
            # Check if any dates failed to parse
            if df['date'].isna().any():
                bad_dates = df[df['date'].isna()]
                logger.error("Some dates failed to parse:")
                logger.error(f"Problem rows:\n{bad_dates}")
                raise ValueError(f"{df['date'].isna().sum()} dates failed to parse")
        except Exception as e:
            logger.error(f"Error converting date: {str(e)}")
            logger.error(f"Sample date values: {df['date'].head()}")
            logger.error(f"Sample time values: {df['time'].head()}")
            raise ValueError(f"Failed to parse date format in detailed format. Error: {str(e)}")

        # Map columns to standardized names
        standardized_mapping = {
            '% date': 'date',
            '% time': 'time',
            '% duration': 'duration',
            '% a number': 'anumber',
            '% b number': 'bnumber',
            '% calltype': 'call_type',
            '% direction': 'direction',
            '% c number': 'cnumber',
            '% a imei': 'imei',
            '% b imei': 'b_imei',
            '% a imei type': 'imei_type',
            '% b imei type': 'b_imei_type',
            '% a imsi': 'imsi',
            '% b imsi': 'b_imsi',
            '% a lac/cid': 'lac_ci',
            '% b lac/cid': 'b_lac_ci',
            '% a sitename': 'sitename',
            '% b sitename': 'b_sitename',
            '% a lat': 'latitude',
            '% a long': 'longitude',
            '% b lat': 'b_latitude',
            '% b long': 'b_longitude'
        }
        
        # Rename columns according to the mapping
        df = df.rename(columns=standardized_mapping)
        
        # Keep all relevant columns including B-side data
        keep_columns = [
            'call_type', 'anumber', 'bnumber', 'date', 'duration',
            'imei', 'b_imei', 'imei_type', 'b_imei_type',
            'imsi', 'b_imsi', 'lac_ci', 'b_lac_ci',
            'sitename', 'b_sitename', 'direction',
            'latitude', 'longitude', 'b_latitude', 'b_longitude'
        ]
        
        logger.debug(f"Available columns after mapping: {list(df.columns)}")
        
        # Only keep columns that exist
        existing_columns = [col for col in keep_columns if col in df.columns]
        df = df[existing_columns]
        
        # Clean phone numbers
        df['anumber'] = df['anumber'].str.replace(r'^\+', '', regex=True)
        df['bnumber'] = df['bnumber'].str.replace(r'^\+', '', regex=True)

        # Filter out invalid B numbers
        df = CDRProcessor._filter_invalid_bnumbers(df)

        logger.debug(f"Final columns after standardization: {list(df.columns)}")
        
        return df
    
    @staticmethod
    def process_cdr_file(file_content: bytes, session_id: str, db: Session) -> int:
        """Processes CDR file and adds it to session"""
        try:
            # Read CSV file
            logger.error("Reading CSV file")
            try:
                # Try reading with comma separator first
                df = pd.read_csv(
                    io.BytesIO(file_content),
                    sep=',',
                    skipinitialspace=True,
                    encoding='utf-8',
                    keep_default_na=False,
                    dtype=str
                )
                
                # If we got only one column, try pipe separator
                if len(df.columns) == 1:
                    logger.error("File appears to be pipe-separated, retrying with | separator")
                    df = pd.read_csv(
                        io.BytesIO(file_content),
                        sep='|',
                        skipinitialspace=True,
                        encoding='utf-8',
                        keep_default_na=False,
                        dtype=str
                    )
                
            except Exception as e:
                logger.error(f"Error reading CSV: {str(e)}")
                raise
            logger.error(f"Read CSV file with shape: {df.shape}")
            
            # Clean column names
            logger.error("Cleaning column names")
            def clean_column_name(col):
                col = str(col).lower().strip()
                # Keep % prefix for initial column mapping
                if col.startswith('%'):
                    col = '% ' + col[1:].strip()
                return col
            
            df.columns = [clean_column_name(col) for col in df.columns]
            logger.error(f"Columns after cleaning: {list(df.columns)}")
            
            # Detect and process format
            file_format = CDRProcessor._detect_file_format(df)
            logger.error(f"Detected format: {file_format}")
            
            # Process detailed format
            if file_format == 'detailed':
                df = CDRProcessor._standardize_detailed_format(df)
                logger.error(f"Standardized columns: {list(df.columns)}")
            
            # Verify all required columns exist
            required_columns = ['call_type', 'anumber', 'bnumber', 'date', 'duration']
            missing = [col for col in required_columns if col not in df.columns]
            if missing:
                raise ValueError(f"Missing required columns: {', '.join(missing)}")
            
            # Process duration
            df['duration'] = df['duration'].astype(str).str.replace(':', '')
            df['duration'] = pd.to_numeric(df['duration'], errors='coerce').fillna(0).astype(int)
            
            # Filter invalid B numbers
            df = CDRProcessor._filter_invalid_bnumbers(df)
            
            # Add data to session
            session_manager = get_session_manager()
            record_count = session_manager.add_cdr_data(db, session_id, df)
            
            logger.info(f"Successfully processed {record_count} records")
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