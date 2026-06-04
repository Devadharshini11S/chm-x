# app/api/routes_scan.py

import os
import shutil
import tempfile
from typing import List, Optional, Literal

from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.models import ScanResponse, MatchItem, ScanFile, Scan
from app.services.scanner_service import scan_path

router = APIRouter(prefix="/api", tags=["scan"])


# ---------- Pydantic request models ----------

class ScanRequest(BaseModel):
    root_path: str
    case_id: Optional[str] = None
    assessed_by: Optional[str] = None
    mode: str = "monitor"
    scan_type: Literal["integrity", "metadata", "ai_detection", "full_evidence"] = "full_evidence"


# ---------- DB dependency ----------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- Existing scan endpoints ----------

@router.post("/scan", response_model=ScanResponse)
def scan_folder(req: ScanRequest):
    if not os.path.exists(req.root_path):
        raise HTTPException(status_code=400, detail="Path does not exist")
    if not os.path.isdir(req.root_path):
        raise HTTPException(status_code=400, detail="Path is not a directory")
    return scan_path(
        req.root_path,
        case_id=req.case_id,
        assessed_by=req.assessed_by,
        mode=req.mode,
        scan_type=req.scan_type,
    )


@router.post("/upload-scan", response_model=ScanResponse)
async def upload_scan(
    case_id: Optional[str] = None,
    assessed_by: Optional[str] = None,
    scan_type: Literal["integrity", "metadata", "ai_detection", "full_evidence"] = "full_evidence",
    files: List[UploadFile] = File(...),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    tmp_dir = tempfile.mkdtemp(prefix="chmx-upload-")
    try:
        for f in files:
            dest = os.path.join(tmp_dir, f.filename)
            with open(dest, "wb") as out:
                while True:
                    chunk = await f.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)

        resp = scan_path(
            tmp_dir,
            case_id=case_id,
            assessed_by=assessed_by,
            mode="monitor",
            scan_type=scan_type,
        )
        return resp
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.post("/scan/filter", response_model=List[MatchItem])
def filter_matches(
    req: ScanRequest,
    status: Optional[str] = Query(None, description="Filter by status: new / modified / intact"),
):
    if not os.path.exists(req.root_path):
        raise HTTPException(status_code=400, detail="Path does not exist")
    if not os.path.isdir(req.root_path):
        raise HTTPException(status_code=400, detail="Path is not a directory")

    resp = scan_path(
        req.root_path,
        case_id=req.case_id,
        assessed_by=req.assessed_by,
        mode=req.mode,
        scan_type=req.scan_type,
    )
    items = resp.matches
    if status:
        items = [m for m in items if m.status == status]
    return items


# ---------- Metadata Investigation endpoint ----------

@router.get("/scan/{scan_id}/metadata-files")
def get_scan_metadata_files(
    scan_id: str,
    db: Session = Depends(get_db),
):
    """
    Returns per-file hashes + metadata + origin_guess for a completed scan.
    Used by the CLI show_metadata / show_full_metadata / investigation views.
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    files = (
        db.query(ScanFile)
        .filter(ScanFile.scan_id == scan_id)
        .all()
    )

    results = []
    for f in files:
        item = {
            "file_path": f.file_path,
            "status": f.status,
            "score": getattr(f, "similarity_score", None),
            "sha_new": getattr(f, "sha_new", None),
            "fuzzy_new": getattr(f, "fuzzy_new", None),
            "phash": getattr(f, "phash", None),
            "clean_metadata": getattr(f, "clean_metadata", None),
            "origin_guess": getattr(f, "origin_guess", None),
            "has_gps": getattr(f, "has_gps", None),
            "gps_lat": getattr(f, "gps_lat", None),
            "gps_lon": getattr(f, "gps_lon", None),
            # keep gps_accuracy_m for backward compat if present
            "gps_accuracy_m": getattr(f, "gps_accuracy_m", None),
            # NEW: human-readable place and full metadata JSON
            "gps_place": getattr(f, "gps_place", None),
            "meta_full": getattr(f, "meta_full", None),
        }

        # Optional fields: only include if they exist on the model
        if hasattr(f, "sha_old"):
            item["sha_old"] = f.sha_old
        if hasattr(f, "fuzzy_old"):
            item["fuzzy_old"] = f.fuzzy_old
        if hasattr(f, "phash_old"):
            item["phash_old"] = f.phash_old

        results.append(item)

    return results
