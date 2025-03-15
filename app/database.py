from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import OperationalError, DisconnectionError
import time
import logging
from app.config import settings

logger = logging.getLogger(__name__)

# Konfigurasi pool
POOL_SIZE = 5
MAX_OVERFLOW = 10
POOL_RECYCLE = 3600  # Recycle koneksi setiap 1 jam
POOL_TIMEOUT = 30
POOL_PRE_PING = True  # Verifikasi koneksi sebelum digunakan

# Buat engine database dengan connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_recycle=POOL_RECYCLE,
    pool_timeout=POOL_TIMEOUT,
    pool_pre_ping=POOL_PRE_PING,
    connect_args={"sslmode": "prefer"}  # Gunakan SSL jika tersedia, tapi tidak wajib
)

# Event handler untuk koneksi
@event.listens_for(engine, "connect")
def connect(dbapi_connection, connection_record):
    logger.debug("Database connection established")

@event.listens_for(engine, "checkout")
def checkout(dbapi_connection, connection_record, connection_proxy):
    logger.debug("Database connection checked out")

@event.listens_for(engine, "checkin")
def checkin(dbapi_connection, connection_record):
    logger.debug("Database connection checked in")

# Fungsi untuk menangani reconnect
def handle_db_connection(max_retries=3, retry_delay=1):
    """Decorator untuk menangani koneksi database dengan retry"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except (OperationalError, DisconnectionError) as e:
                    retries += 1
                    logger.warning(f"Database connection error: {str(e)}. Retry {retries}/{max_retries}")
                    if retries >= max_retries:
                        logger.error(f"Max retries reached. Database connection failed: {str(e)}")
                        raise
                    time.sleep(retry_delay)
        return wrapper
    return decorator

# Buat session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Buat base class untuk model
Base = declarative_base()

# Dependency untuk mendapatkan database session dengan retry
def get_db():
    db = SessionLocal()
    try:
        # Periksa koneksi dengan menjalankan ping (gunakan text() dari sqlalchemy)
        db.execute(text("SELECT 1"))
        yield db
    except Exception as e:
        logger.error(f"Error dengan koneksi database: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

# Inisialisasi database
@handle_db_connection(max_retries=5, retry_delay=2)
def init_db():
    try:
        # Buat semua tabel jika belum ada
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise 