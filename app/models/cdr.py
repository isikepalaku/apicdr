from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class CDRRecord(BaseModel):
    """Model untuk satu record CDR"""
    call_type: str = Field(..., description="Tipe panggilan (Voice MO, VAS, dll)")
    anumber: str = Field(..., description="Nomor penelepon")
    bnumber: str = Field(..., description="Nomor yang dihubungi")
    cnumber: Optional[str] = Field(None, description="Nomor tambahan")
    date: datetime = Field(..., description="Tanggal dan waktu panggilan")
    duration: int = Field(..., description="Durasi panggilan dalam detik")
    lac_ci: Optional[str] = Field(None, description="Location Area Code dan Cell ID")
    imei: Optional[str] = Field(None, description="International Mobile Equipment Identity")
    imei_type: Optional[str] = Field(None, description="Tipe perangkat IMEI")
    imsi: Optional[str] = Field(None, description="International Mobile Subscriber Identity")
    sitename: Optional[str] = Field(None, description="Nama lokasi BTS")
    direction: Optional[str] = Field(None, description="Arah panggilan (incoming/outgoing)")
    latitude: Optional[str] = Field(None, description="Latitude lokasi")
    longitude: Optional[str] = Field(None, description="Longitude lokasi")

class CDRUploadResponse(BaseModel):
    """Response untuk upload CDR"""
    success: bool = True
    message: str
    records_processed: int
    session_id: str

class CDRAnalysisRequest(BaseModel):
    """Request untuk analisis CDR"""
    session_id: str
    filter_options: Optional[dict] = None

class GraphData(BaseModel):
    """Model untuk data graph yang akan dikembalikan ke frontend"""
    nodes: List[dict]
    edges: List[dict]

class SessionInfo(BaseModel):
    """Informasi tentang session"""
    session_id: str
    created_at: datetime
    record_count: int
    description: Optional[str] = None

class SessionListResponse(BaseModel):
    """Response untuk daftar session"""
    sessions: List[SessionInfo]

class SessionCreateRequest(BaseModel):
    """Request untuk membuat session baru"""
    name: str = Field(..., description="Nama session")
    description: Optional[str] = None

class SessionCreateResponse(BaseModel):
    """Response untuk pembuatan session"""
    success: bool = True
    session_id: str
    message: str 