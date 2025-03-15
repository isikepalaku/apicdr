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
        columns = set(col.lower().strip('% ') for col in df.columns)
        if any('a number' in col for col in columns) and any('calltype' in col for col in columns):
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
        
        # Standardize column names first
        df.columns = [col.lower().strip('% ') for col in df.columns]
        logger.debug(f"Columns after standardization: {list(df.columns)}")
        
        # Create comprehensive mapping for all possible columns
        logger.debug("Applying column mapping")
        column_mapping = {
            'a number': 'anumber',
            'b number': 'bnumber',
            'c number': 'cnumber',
            'calltype': 'call_type',
            'duration': 'duration',
            'a imei': 'imei',
            'b imei': 'b_imei',
            'a imei type': 'imei_type',
            'b imei type': 'b_imei_type',
            'a imsi': 'imsi',
            'b imsi': 'b_imsi',
            'a sitename': 'sitename',
            'b sitename': 'b_sitename',
            'a lac/cid': 'lac_ci',
            'b lac/cid': 'b_lac_ci',
            'direction': 'direction',
            'a lat': 'latitude',
            'a long': 'longitude',
            'b lat': 'b_latitude',
            'b long': 'b_longitude'
        }

        # Log original columns for debugging
        logger.debug(f"Original columns before mapping: {list(df.columns)}")
        
        # Rename columns but keep 'date' and 'time' as is for now
        df = df.rename(columns=column_mapping)
        
        # Handle duration - convert : to empty if present
        if 'duration' in df.columns:
            df['duration'] = df['duration'].replace(':', '0')
            df['duration'] = pd.to_numeric(df['duration'], errors='coerce').fillna(0).astype(int)
        
        # Combine date and time
        df['date'] = pd.to_datetime(
            df['date'] + ' ' + df['time'],
            format='%d/%b/%y %H:%M:%S'
        )
        
        # Handle date before dropping columns
        try:
            df['date'] = pd.to_datetime(
                df['date'] + ' ' + df['time'],
                format='%d/%b/%y %H:%M:%S',
                errors='coerce'
            )
        except Exception as e:
            logger.error(f"Error converting date: {str(e)}")
            logger.error(f"Sample date values: {df['date'].head()}")
            logger.error(f"Sample time values: {df['time'].head()}")
            raise ValueError(f"Failed to parse date format in detailed format. Error: {str(e)}")

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
            
            # Keep original columns for debugging
            original_columns = list(df.columns)
            logger.debug(f"Original columns: {original_columns}")
            
            # Standardize column names
            df.columns = [col.lower().strip('% ') for col in df.columns]
            logger.debug(f"Standardized columns: {list(df.columns)}")
            
            # Detect and process format
            file_format = CDRProcessor._detect_file_format(df)
            logger.info(f"Detected file format: {file_format}")
            
            if file_format == 'detailed':
                df = CDRProcessor._standardize_detailed_format(df)
                logger.debug(f"Columns after standardization: {list(df.columns)}")
            
            # Verify required columns
            required_columns = ['call_type', 'anumber', 'bnumber', 'date', 'duration']
            for col in required_columns:
                if col not in df.columns:
                    raise ValueError(f"Required column {col} not found in CDR file. Available columns: {list(df.columns)}")
            
            # Handle different date formats with improved error handling
            try:
                logger.debug("Starting date conversion")
                logger.debug(f"Current date column values: {df['date'].head()}")
                
                if file_format == 'detailed':
                    if 'time' not in df.columns:
                        logger.error("Time column missing in detailed format")
                        logger.error(f"Available columns: {list(df.columns)}")
                        raise ValueError("Time column missing in detailed format")
                    
                    # Try parsing date and time together
                    for date_format in ['%d/%b/%y', '%d/%b/%Y']:
                        try:
                            logger.debug(f"Attempting date format: {date_format}")
                            df['parsed_date'] = pd.to_datetime(
                                df['date'].astype(str) + ' ' + df['time'].astype(str),
                                format=f'{date_format} %H:%M:%S',
                                errors='raise'
                            )
                            df['date'] = df['parsed_date']
                            df = df.drop(['parsed_date', 'time'], axis=1, errors='ignore')
                            logger.info(f"Successfully parsed dates using format: {date_format}")
                            break
                        except Exception as format_error:
                            logger.debug(f"Format {date_format} failed: {str(format_error)}")
                            continue
                    
                    # If no format worked, try one last time with flexible parsing
                    if 'parsed_date' not in df.columns:
                        logger.warning("Attempting flexible date parsing")
                        df['date'] = pd.to_datetime(
                            df['date'].astype(str) + ' ' + df['time'].astype(str),
                            errors='coerce'
                        )
                else:
                    # For standard format, try multiple patterns
                    df['date'] = pd.to_datetime(df['date'], errors='coerce')
                
                # Validate results
                if df['date'].isna().any():
                    bad_dates = df[df['date'].isna()]
                    logger.error("Some dates failed to parse:")
                    logger.error(f"Problem rows:\n{bad_dates[['date', 'time'] if 'time' in bad_dates else ['date']].head()}")
                    raise ValueError(f"{df['date'].isna().sum()} dates failed to parse. Check logs for details.")
                
                logger.info("Date conversion completed successfully")
                logger.debug(f"Sample converted dates:\n{df['date'].head()}")
                
            except Exception as e:
                logger.error(f"Date conversion failed: {str(e)}")
                if 'date' in df.columns:
                    logger.error(f"Original date values:\n{df['date'].head()}")
                if 'time' in df.columns:
                    logger.error(f"Time values:\n{df['time'].head()}")
                raise ValueError(f"Date conversion error: {str(e)}")
            
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