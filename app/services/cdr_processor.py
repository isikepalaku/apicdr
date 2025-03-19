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
            
        logger.error(f"Format detection - Available columns: {columns}")
        
        # Check for standard format (simple column names)
        standard_columns = {'anumber', 'bnumber', 'date', 'duration'}
        has_standard = all(col in columns for col in standard_columns)
        logger.error(f"Format detection - Has standard columns: {has_standard}")
        
        if has_standard:
            return 'standard'
            
        # More flexible check for Excel files with different column naming patterns
        excel_number_patterns = {'a_number', 'phone_a', 'msisdn_a', 'caller', 'calling_number', 'anumber'}
        excel_bnumber_patterns = {'b_number', 'phone_b', 'msisdn_b', 'called', 'called_number', 'bnumber'}
        excel_date_patterns = {'datetime', 'timestamp', 'call_timestamp', 'date_time', 'call_date', 'start_time', 'date'}
        excel_duration_patterns = {'duration', 'call_duration', 'duration_sec', 'duration_seconds', 'call_length'}

        has_anumber = any(any(pattern in col for col in columns) for pattern in excel_number_patterns)
        has_bnumber = any(any(pattern in col for col in columns) for pattern in excel_bnumber_patterns)
        has_date = any(any(pattern in col for col in columns) for pattern in excel_date_patterns)
        has_duration = any(any(pattern in col for col in columns) for pattern in excel_duration_patterns)

        logger.error(f"Format detection - Excel patterns found:")
        logger.error(f"A-number: {has_anumber}")
        logger.error(f"B-number: {has_bnumber}")
        logger.error(f"Date: {has_date}")
        logger.error(f"Duration: {has_duration}")

        if has_anumber and has_bnumber and has_date and has_duration:
            return 'standard'
            
        # Default to detailed if we have date and time columns
        has_date_time = 'date' in columns and 'time' in columns
        logger.error(f"Format detection - Has date and time columns: {has_date_time}")
        
        if has_date_time:
            return 'detailed'
            
        logger.error("Format detection - Defaulting to standard format")
        return 'standard'

    @staticmethod
    def _filter_invalid_bnumbers(df: pd.DataFrame) -> pd.DataFrame:
        """
        Removes records with invalid B numbers, but keeps GPRS records
        """
        # Don't filter B numbers for GPRS records
        gprs_mask = df['call_type'].str.upper() == 'GPRS'
        non_gprs_mask = ~gprs_mask
        
        # Only filter invalid B numbers for non-GPRS records
        invalid_numbers = ['8331', '100', '363', '8999']
        invalid_mask = df['bnumber'].astype(str).isin(invalid_numbers)
        
        # Keep records that are either GPRS or have valid B numbers
        return df[gprs_mask | (non_gprs_mask & ~invalid_mask)]

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
            # Try to read file in different formats
            logger.error("Reading input file")
            try:
                # First try as XLSX
                try:
                    df = pd.read_excel(
                        io.BytesIO(file_content),
                        engine='openpyxl',
                        dtype=str
                    )
                    # Handle Excel date/time conversion
                    if 'date' in df.columns:
                        logger.error(f"Raw date values: {df['date'].head()}")
                        
                        # Check if we have Excel serial dates
                        try:
                            numeric_dates = pd.to_numeric(df['date'], errors='coerce')
                            if not numeric_dates.isna().all():
                                # Convert Excel serial dates to datetime
                                df['date'] = pd.TimedeltaIndex(numeric_dates, unit='D') + pd.Timestamp('1899-12-30')
                                logger.error("Successfully converted Excel serial dates")
                                success = True
                            else:
                                success = False
                        except Exception as e:
                            logger.error(f"Not Excel serial dates: {str(e)}")
                            success = False
                        
                        # If not Excel serial dates, try various string formats
                        if not success:
                            # Try multiple date formats
                            date_formats = [
                                None,  # Let pandas auto-detect
                                '%Y-%m-%d %H:%M:%S',
                                '%d/%m/%Y %H:%M:%S',
                                '%d/%b/%y %H:%M:%S',
                                '%d-%m-%Y %H:%M:%S',
                                '%Y/%m/%d %H:%M:%S',
                                '%m/%d/%Y %H:%M:%S',
                                '%Y-%m-%d',
                                '%d/%m/%Y',
                                '%Y%m%d%H%M%S',
                                '%d-%b-%Y %H:%M:%S'
                            ]
                            
                            for fmt in date_formats:
                                try:
                                    if fmt is None:
                                        df['date'] = pd.to_datetime(df['date'])
                                    else:
                                        df['date'] = pd.to_datetime(df['date'], format=fmt)
                                    success = True
                                    logger.error(f"Successfully parsed dates with format: {fmt or 'auto'}")
                                    break
                                except Exception as e:
                                    logger.error(f"Failed to parse dates with format {fmt}: {str(e)}")
                                    continue
                        
                        if not success:
                            raise ValueError("Failed to parse date values in any supported format")
                        
                        logger.error(f"Parsed date values: {df['date'].head()}")
                        
                        logger.error(f"Parsed date values: {df['date'].head()}")
                    
                    # Ensure duration is numeric
                    if 'duration' in df.columns:
                        df['duration'] = pd.to_numeric(df['duration'].astype(str).str.replace(':', ''), errors='coerce').fillna(0).astype(int)
                    
                    logger.error("Successfully read XLSX file")
                    logger.error(f"Sample data - First row: {df.iloc[0].to_dict()}")
                except Exception as xlsx_error:
                    logger.error(f"Not an XLSX file, trying CSV formats: {str(xlsx_error)}")
                    # Try reading with different encodings
                    encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
                    last_error = None
                    df = None
                    
                    # Try comma-separated first
                    for encoding in encodings:
                        try:
                            df = pd.read_csv(
                                io.BytesIO(file_content),
                                sep=',',
                                skipinitialspace=True,
                                encoding=encoding,
                                keep_default_na=False,
                                dtype=str
                            )
                            logger.error(f"Successfully read CSV with {encoding} encoding")
                            break
                        except Exception as e:
                            last_error = e
                            logger.error(f"Failed to read with {encoding} encoding: {str(e)}")
                    
                    # If comma-separated failed or resulted in one column, try pipe-separated
                    if df is None or (df is not None and len(df.columns) == 1):
                        logger.error("Attempting to read as pipe-separated file")
                        for encoding in encodings:
                            try:
                                df = pd.read_csv(
                                    io.BytesIO(file_content),
                                    sep='|',
                                    skipinitialspace=True,
                                    encoding=encoding,
                                    keep_default_na=False,
                                    dtype=str
                                )
                                logger.error(f"Successfully read pipe-separated file with {encoding} encoding")
                                break
                            except Exception as e:
                                last_error = e
                                logger.error(f"Failed to read pipe-separated with {encoding} encoding: {str(e)}")
                    
                    # If we still don't have valid data, raise the last error
                    if df is None:
                        raise last_error
            except Exception as e:
                logger.error(f"Error reading file: {str(e)}")
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
            
            # Clean and standardize column names
            df.columns = [clean_column_name(col) for col in df.columns]
            logger.error(f"Columns after initial cleaning: {list(df.columns)}")
            
            # Additional column name standardization for Excel files
            excel_column_mapping = {
                # Number variations
                'a_number': 'anumber',
                'b_number': 'bnumber',
                'c_number': 'cnumber',
                'phone_a': 'anumber',
                'phone_b': 'bnumber',
                'phone_c': 'cnumber',
                'phone_number_a': 'anumber',
                'phone_number_b': 'bnumber',
                'msisdn_a': 'anumber',
                'msisdn_b': 'bnumber',
                'caller': 'anumber',
                'called': 'bnumber',
                'calling_number': 'anumber',
                'called_number': 'bnumber',
                
                # Date/time variations
                'datetime': 'date',
                'timestamp': 'date',
                'call_timestamp': 'date',
                'date_time': 'date',
                'call_date': 'date',
                'call_time': 'time',
                'start_time': 'date',
                'end_time': 'end_date',
                
                # Call type variations
                'call type': 'call_type',
                'calltype': 'call_type',
                'type': 'call_type',
                'call_category': 'call_type',
                
                # Duration variations
                'call_duration': 'duration',
                'duration_sec': 'duration',
                'duration_seconds': 'duration',
                'call_length': 'duration'
            }
            
            # Apply Excel-specific mapping
            df.columns = [excel_column_mapping.get(col, col) for col in df.columns]
            logger.error(f"Columns after Excel mapping: {list(df.columns)}")
            
            # Detect and process format
            file_format = CDRProcessor._detect_file_format(df)
            logger.error(f"Detected format: {file_format}")
            
            # Process detailed format
            if file_format == 'detailed':
                df = CDRProcessor._standardize_detailed_format(df)
                logger.error(f"Standardized columns: {list(df.columns)}")
            
            # Verify all required columns exist
            required_columns = ['call_type', 'anumber', 'bnumber', 'date', 'duration']
            logger.error(f"Data validation - Current columns: {list(df.columns)}")
            missing = [col for col in required_columns if col not in df.columns]
            if missing:
                raise ValueError(f"Missing required columns: {', '.join(missing)}")
            
            logger.error(f"Data validation - Row count before duration processing: {len(df)}")
            logger.error(f"Data validation - Sample data before processing:\n{df.head(1).to_dict('records')}")
            
            # Process duration
            df['duration'] = df['duration'].astype(str).str.replace(':', '')
            df['duration'] = pd.to_numeric(df['duration'], errors='coerce').fillna(0).astype(int)
            
            logger.error(f"Data validation - Row count after duration processing: {len(df)}")
            
            # Filter invalid B numbers
            df_before_filter = len(df)
            df = CDRProcessor._filter_invalid_bnumbers(df)
            df_after_filter = len(df)
            
            logger.error(f"Data validation - Rows before B number filtering: {df_before_filter}")
            logger.error(f"Data validation - Rows after B number filtering: {df_after_filter}")
            logger.error(f"Data validation - Final sample data:\n{df.head(1).to_dict('records')}")
            
            # Final data validation before saving
            logger.error("Performing final data validation")
            initial_rows = len(df)
            
            # Separate GPRS and non-GPRS records
            gprs_records = df[df['call_type'].str.upper() == 'GPRS'].copy()
            non_gprs_records = df[df['call_type'].str.upper() != 'GPRS'].copy()
            
            logger.error(f"Initial split - GPRS records: {len(gprs_records)}, Non-GPRS records: {len(non_gprs_records)}")
            
            # Validate non-GPRS records
            if len(non_gprs_records) > 0:
                for col in required_columns:
                    non_gprs_records = non_gprs_records[non_gprs_records[col].notna()]
                    non_gprs_records = non_gprs_records[non_gprs_records[col].astype(str).str.strip() != '']
                non_gprs_records = non_gprs_records[non_gprs_records['anumber'].astype(str).str.len() >= 4]
                non_gprs_records = non_gprs_records[non_gprs_records['bnumber'].astype(str).str.len() >= 4]
            
            # Validate GPRS records (less strict validation)
            if len(gprs_records) > 0:
                # For GPRS, we only require valid A number and date
                required_gprs_cols = ['call_type', 'anumber', 'date']
                for col in required_gprs_cols:
                    gprs_records = gprs_records[gprs_records[col].notna()]
                    gprs_records = gprs_records[gprs_records[col].astype(str).str.strip() != '']
                gprs_records = gprs_records[gprs_records['anumber'].astype(str).str.len() >= 4]
            
            # Combine the validated records
            df = pd.concat([gprs_records, non_gprs_records], ignore_index=True)
            
            # Common validations for all records
            df = df[df['date'].notna()]  # Ensure dates are valid
            df = df[pd.to_numeric(df['duration'], errors='coerce').fillna(0) >= 0]  # Allow 0 duration
            
            rows_after_validation = len(df)
            logger.error(f"Validation results:")
            logger.error(f"- Valid GPRS records: {len(gprs_records)}")
            logger.error(f"- Valid non-GPRS records: {len(non_gprs_records)}")
            logger.error(f"Final validation - Initial rows: {initial_rows}")
            logger.error(f"Final validation - Rows after validation: {rows_after_validation}")
            logger.error(f"Final validation - Removed {initial_rows - rows_after_validation} invalid records")
            
            if rows_after_validation == 0:
                raise ValueError("No valid records found after data validation")
            
            # Add data to session
            session_manager = get_session_manager()
            record_count = session_manager.add_cdr_data(db, session_id, df)
            
            logger.info(f"Successfully processed and saved {record_count} valid records")
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