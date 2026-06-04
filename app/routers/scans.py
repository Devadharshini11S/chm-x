# backend/app/routers/scans.py
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class Gps(BaseModel):
  lat: float | None = None
  lon: float | None = None

class Exif(BaseModel):
  make: str | None = None
  model: str | None = None
  software: str | None = None
  datetime: str | None = None
  width: int | None = None
  height: int | None = None
  gps: Gps | None = None

class PerceptualHashes(BaseModel):
  ahash: str | None = None
  phash: str | None = None
  chhash: str | None = None
  domihash: str | None = None

class HashInfo(BaseModel):
  sha256: str | None = None
  perceptual: PerceptualHashes = PerceptualHashes()
  has_known_match: bool = False

class MetadataItem(BaseModel):
  id: str
  path: str
  size_bytes: int
  exif: Exif
  hash: HashInfo

class MetadataResponse(BaseModel):
  items: List[MetadataItem]
  total: int

@router.get("/scans/{scan_id}/metadata", response_model=MetadataResponse)
def get_scan_metadata(scan_id: str):
  # TODO: hook into your real scan/EXIF data
  return MetadataResponse(items=[], total=0)

@router.get("/scans/{scan_id}/report")
def get_scan_report(scan_id: str):
  # TODO: return a real report file
  raise HTTPException(status_code=404, detail="Report not implemented")
