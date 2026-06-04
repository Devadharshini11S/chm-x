from datetime import datetime
from typing import Dict, List, Optional, Any

from pydantic import BaseModel
from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    Float,
    Boolean,
    Text,
    Index,
    JSON,
)
from sqlalchemy.orm import relationship

from app.core.db import Base, engine


# ---------- SQLALCHEMY TABLES ----------


class Case(Base):
    __tablename__ = "cases"

    id = Column(String, primary_key=True, index=True)      # case number
    name = Column(String, nullable=False)                  # short title
    description = Column(Text, nullable=True)              # case description
    created_at = Column(DateTime, default=datetime.utcnow)
    assessed_by = Column(String, nullable=True)            # who assessed

    scans = relationship("Scan", back_populates="case")


class Scan(Base):
    __tablename__ = "scans"

    id = Column(String, primary_key=True, index=True)      # scan_id
    case_id = Column(String, ForeignKey("cases.id"), index=True, nullable=True)
    root_path = Column(Text, nullable=False)
    mode = Column(String, default="monitor")               # baseline / monitor
    status = Column(String, default="queued")              # queued/running/done/failed
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    total_files = Column(Integer, default=0)
    new_files = Column(Integer, default=0)
    modified_files = Column(Integer, default=0)
    removed_files = Column(Integer, default=0)

    case = relationship("Case", back_populates="scans")
    files = relationship("ScanFile", back_populates="scan")


class ScanFile(Base):
    __tablename__ = "scan_files"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    scan_id = Column(String, ForeignKey("scans.id"), index=True)

    file_path = Column(Text, index=True)
    size_bytes = Column(Integer)

    # filesystem MAC times
    mtime = Column(DateTime)   # last modified
    ctime = Column(DateTime)   # created / metadata changed
    atime = Column(DateTime)   # last accessed

    mime_type = Column(String, nullable=True)
    author = Column(String, nullable=True)          # EXIF Artist or doc author
    exif_datetime = Column(String, nullable=True)   # EXIF DateTimeOriginal/DateTime

    # compact EXIF/metadata summary (for Metadata Investigation)
    clean_metadata = Column(JSON, nullable=True)

    # quick GPS flag for queries / UI
    has_gps = Column(Boolean, default=False)

    # precise GPS coordinates and human-readable place
    gps_lat = Column(Float, nullable=True)
    gps_lon = Column(Float, nullable=True)
    gps_place = Column(String, nullable=True)  # e.g. "Warsaw, Poland"

    # origin classification based on metadata + hashes
    origin_guess = Column(String, nullable=True)

    # hashes
    sha_new = Column(String, index=True)
    sha_old = Column(String, index=True)
    fuzzy_new = Column(Text)
    fuzzy_old = Column(Text)

    similarity_score = Column(Float)
    status = Column(String)      # new / modified / intact / unknown
    risk_level = Column(String)  # ok / suspicious_modified / changed
    is_baseline_match = Column(Boolean, default=False)

    # perceptual hash (for visual similarity) – stored for the "new" file
    phash = Column(String, nullable=True)

    # list of best ssdeep matches for this file
    top_matches = Column(JSON, nullable=True)  # [{"path": "...", "similarity": 94}, ...]

    # NEW: full ExifTool JSON (for show_full_metadata in CLI)
    meta_full = Column(JSON, nullable=True)

    scan = relationship("Scan", back_populates="files")


Index("ix_scan_files_path", ScanFile.file_path)
Index("ix_scan_files_scan_status", ScanFile.scan_id, ScanFile.status)
# NOTE: don't define ix_scan_files_sha_new again to avoid duplicate index error


def init_db():
    Base.metadata.create_all(bind=engine)


# ---------- PYDANTIC MODELS (API) ----------


class ScanSummary(BaseModel):
    scan_id: str
    started_at: datetime
    finished_at: datetime
    total_files: int
    total_matches: int
    scan_time_ms: int
    file_types: Dict[str, int]
    score_buckets: Dict[str, int]


class CleanMetadata(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    software: Optional[str] = None
    datetime: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    has_gps: bool = False

    # forensic enrichment
    edited_with: Optional[str] = None   # e.g. PicsArt, Canva, InShot
    ai_tool: Optional[str] = None       # e.g. Midjourney, DALL·E, Gemini

    # fuzzy hash over full ExifTool metadata
    meta_ssdeep: Optional[str] = None

    class Config:
        extra = "allow"  # allow additional keys from clean_metadata (if any)


class MatchItem(BaseModel):
    id: str
    file_path: str
    file_type: str

    # last vs new hashes
    sha_new: str
    sha_old: str
    fuzzy_new: str
    fuzzy_old: str
    score: float
    status: str
    risk_level: str
    timestamp: datetime

    # metadata + origin fields for Metadata Investigation
    clean_metadata: Optional[CleanMetadata] = None
    origin_guess: Optional[str] = None
    has_gps: Optional[bool] = None

    # GPS + place, as exposed by ScanFile
    gps_lat: Optional[float] = None
    gps_lon: Optional[float] = None
    gps_place: Optional[str] = None

    # perceptual hash values
    phash: Optional[str] = None        # new pHash
    phash_old: Optional[str] = None    # old pHash from baseline (last)

    # fixed original baseline hashes
    sha_initial: Optional[str] = None
    fuzzy_initial: Optional[str] = None
    phash_initial: Optional[str] = None

    # top ssdeep matches inside this scan
    top_matches: Optional[List[Dict[str, Any]]] = None  # {"path": str, "similarity": float}


class ScanResponse(BaseModel):
    summary: ScanSummary
    matches: List[MatchItem]
