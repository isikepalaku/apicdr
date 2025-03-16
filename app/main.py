from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.routers import cdr, auth, session
from app.services.session_manager import get_session_manager
from app.utils.logging_config import setup_logging
from app.utils.api_key_auth import verify_api_key
from app.database import init_db
from app.config import settings
import logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="API untuk menganalisis data CDR dan menghubungkan entitas terkait",
    version=settings.APP_VERSION
)

# Konfigurasi CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "https://cdr.reverse.id"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Inisialisasi pada startup
@app.on_event("startup")
async def startup_event():
    logger.info("Starting CDR Analyzer API")
    
    # Inisialisasi database
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise
    
    # Inisialisasi session manager
    try:
        session_manager = get_session_manager()
        session_manager.initialize()
        logger.info("Session manager initialized")
    except Exception as e:
        logger.error(f"Error initializing session manager: {str(e)}")
        raise

# Tambahkan router
# Add routers with API key authentication
app.include_router(
    auth.router, 
    prefix="/api", 
    tags=["Authentication"],
    dependencies=[Depends(verify_api_key)]
)
app.include_router(
    session.router, 
    prefix="/api", 
    tags=["Session"],
    dependencies=[Depends(verify_api_key)]
)
app.include_router(
    cdr.router, 
    prefix="/api", 
    tags=["CDR Analysis"],
    dependencies=[Depends(verify_api_key)]
)

@app.get("/")
async def root():
    return {"message": "Selamat datang di CDR Analyzer API"}

@app.get("/health")
async def health_check():
    """
    Health check endpoint for container monitoring
    """
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", "3001"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
