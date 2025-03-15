from supabase import create_client, Client
from app.config import settings
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.database_models import User

logger = logging.getLogger(__name__)

class SupabaseService:
    """
    Service untuk berinteraksi dengan Supabase
    """
    
    def __init__(self):
        self.supabase: Optional[Client] = None
        
    def initialize(self):
        """Inisialisasi klien Supabase"""
        try:
            self.supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            logger.info("Supabase client initialized")
        except Exception as e:
            logger.error(f"Error initializing Supabase client: {str(e)}")
            raise
    
    def sign_up(self, email: str, password: str, username: str, full_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Mendaftarkan user baru di Supabase
        
        Args:
            email: Email user
            password: Password user
            username: Username user
            full_name: Nama lengkap user (opsional)
            
        Returns:
            Data user yang berhasil didaftarkan
        """
        try:
            # Daftarkan user di Supabase
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "username": username,
                        "full_name": full_name
                    }
                }
            })
            
            logger.info(f"User registered: {email}")
            return response
        except Exception as e:
            logger.error(f"Error registering user: {str(e)}")
            raise
    
    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """
        Login user di Supabase
        
        Args:
            email: Email user
            password: Password user
            
        Returns:
            Data user yang berhasil login
        """
        try:
            # Login user di Supabase
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            logger.info(f"User logged in: {email}")
            return response
        except Exception as e:
            logger.error(f"Error logging in user: {str(e)}")
            raise
    
    def sync_user_to_db(self, user_data: Dict[str, Any], db: Session) -> User:
        """
        Sinkronisasi data user dari Supabase ke database lokal
        
        Args:
            user_data: Data user dari Supabase
            db: Database session
            
        Returns:
            User object dari database
        """
        try:
            # Cek apakah user_data adalah objek atau dictionary
            if hasattr(user_data, 'id'):
                # Objek User dari Supabase
                user_id = user_data.id
                user_email = user_data.email
                user_metadata = getattr(user_data, 'user_metadata', {}) or {}
                username = user_metadata.get('username', '')
                full_name = user_metadata.get('full_name', '')
            else:
                # Dictionary
                user_id = user_data["id"]
                user_email = user_data["email"]
                user_metadata = user_data.get("user_metadata", {}) or {}
                username = user_metadata.get("username", "")
                full_name = user_metadata.get("full_name", "")
            
            # Cek apakah user sudah ada di database
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                # Buat user baru
                user = User(
                    id=user_id,
                    email=user_email,
                    username=username,
                    full_name=full_name,
                    is_active=True,
                    is_approved=False  # Default tidak disetujui
                )
                db.add(user)
            else:
                # Update data user
                user.email = user_email
                user.username = username or user.username
                user.full_name = full_name or user.full_name
                user.is_active = True
            
            db.commit()
            db.refresh(user)
            
            return user
        except Exception as e:
            db.rollback()
            logger.error(f"Error syncing user to database: {str(e)}")
            raise
    
    def approve_user(self, user_id: str, db: Session) -> User:
        """
        Menyetujui user untuk menggunakan aplikasi
        
        Args:
            user_id: ID user yang akan disetujui
            db: Database session
            
        Returns:
            User object yang diperbarui
        """
        try:
            # Cari user di database
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                raise ValueError(f"User dengan ID {user_id} tidak ditemukan")
            
            # Setujui user
            user.is_approved = True
            db.commit()
            db.refresh(user)
            
            logger.info(f"User approved: {user.email}")
            return user
        except Exception as e:
            db.rollback()
            logger.error(f"Error approving user: {str(e)}")
            raise
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verifikasi token JWT dari Supabase
        
        Args:
            token: Token JWT
            
        Returns:
            Data user jika token valid
        """
        try:
            # Verifikasi token
            response = self.supabase.auth.get_user(token)
            return response
        except Exception as e:
            logger.error(f"Error verifying token: {str(e)}")
            raise

# Singleton instance
_supabase_service = None

def get_supabase_service() -> SupabaseService:
    """Dapatkan instance SupabaseService (singleton)"""
    global _supabase_service
    if _supabase_service is None:
        _supabase_service = SupabaseService()
    return _supabase_service 