import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    """
    Setup logging configuration
    """
    # Buat direktori logs jika belum ada
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Konfigurasi logging
    log_file = os.path.join(log_dir, "cdr_analyzer.log")
    
    # Format log
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Konfigurasi root logger
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            # Log ke file dengan rotasi
            RotatingFileHandler(
                log_file, maxBytes=10485760, backupCount=5
            ),
            # Log ke console
            logging.StreamHandler()
        ]
    )
    
    # Set level untuk library lain
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    
    # Log startup
    logging.info("Logging initialized") 