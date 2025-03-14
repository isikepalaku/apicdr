from datetime import datetime, timedelta
from typing import Optional
import os
import json
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import logging
from app.models.auth import UserInDB, User, TokenData

# Konfigurasi
SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Setup logging
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token", auto_error=False)

# Simpan user dalam file JSON untuk sementara
# Dalam produksi, gunakan database
USERS_FILE = "app/data/users.json"

def initialize_users_file():
    """Inisialisasi file users.json jika belum ada"""
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({"users": []}, f)
        logger.info("Created users file")

def get_users():
    """Dapatkan semua user dari file"""
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        initialize_users_file()
        return {"users": []}

def save_users(users_data):
    """Simpan data user ke file"""
    with open(USERS_FILE, "w") as f:
        json.dump(users_data, f)

def get_user(username: str) -> Optional[UserInDB]:
    """Dapatkan user berdasarkan username"""
    users_data = get_users()
    
    for user in users_data["users"]:
        if user["username"] == username:
            return UserInDB(**user)
    
    return None

def create_user(username: str, email: str, password: str, full_name: Optional[str] = None) -> User:
    """Buat user baru"""
    users_data = get_users()
    
    # Cek apakah username sudah ada
    for user in users_data["users"]:
        if user["username"] == username:
            raise ValueError("Username sudah digunakan")
    
    # Hash password
    hashed_password = get_password_hash(password)
    
    # Buat user baru
    new_user = {
        "username": username,
        "email": email,
        "full_name": full_name,
        "disabled": False,
        "hashed_password": hashed_password
    }
    
    # Tambahkan ke data
    users_data["users"].append(new_user)
    
    # Simpan ke file
    save_users(users_data)
    
    # Kembalikan user tanpa password
    return User(
        username=username,
        email=email,
        full_name=full_name,
        disabled=False
    )

def verify_password(plain_password, hashed_password):
    """Verifikasi password"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Hash password"""
    return pwd_context.hash(password)

def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Autentikasi user"""
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Buat access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[User]:
    """Dapatkan user saat ini dari token"""
    if not token:
        return None
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        token_data = TokenData(username=username)
    except JWTError:
        return None
    
    user = get_user(token_data.username)
    if user is None:
        return None
    
    return User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled
    )

async def get_current_active_user(current_user: Optional[User] = Depends(get_current_user)) -> Optional[User]:
    """Dapatkan user aktif saat ini"""
    if not current_user:
        return None
    if current_user.disabled:
        return None
    return current_user
