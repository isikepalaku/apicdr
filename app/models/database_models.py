from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base

class User(Base):
    """Model untuk user di database"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Session(Base):
    """Model untuk session di database"""
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    record_count = Column(Integer, default=0)
    
    # Relationship
    cdr_records = relationship("CDRRecord", back_populates="session")
    graph_data = Column(JSON, nullable=True)  # Menyimpan data graph dalam format JSON

class CDRRecord(Base):
    """Model untuk record CDR di database"""
    __tablename__ = "cdr_records"
    
    id = Column(Integer, primary_key=True, index=True)
    call_type = Column(String)
    anumber = Column(String, index=True)
    bnumber = Column(String, index=True)
    cnumber = Column(String, nullable=True)
    date = Column(DateTime)
    duration = Column(Integer)
    lac_ci = Column(String, nullable=True)
    imei = Column(String, nullable=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    
    # Relationship
    session = relationship("Session", back_populates="cdr_records") 