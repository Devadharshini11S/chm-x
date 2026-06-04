# app/api/routes_cases.py
from datetime import datetime
from typing import List, Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

ScanType = Literal["file", "folder", "drive", "url", "port", "metadata", "integrity"]


class ScanCreate(BaseModel):
    type: ScanType
    target: str


class CaseCreate(BaseModel):
    case_id: str
    name: str
    assessed_by: str
    description: str
    scans: List[ScanCreate]


class ScanSummary(BaseModel):
    id: str
    type: ScanType
    target: str
    status: Literal["pending", "running", "completed", "failed"]
    started_at: datetime | None = None
    finished_at: datetime | None = None
    report_path: str | None = None


class CaseSummary(BaseModel):
    id: str
    case_id: str
    name: str
    assessed_by: str
    description: str
    created_at: datetime
    last_scan_status: str | None = None


class CaseDetail(CaseSummary):
    scans: List[ScanSummary]


router = APIRouter()

# For now, keep data in memory. Later you can replace this with your DB models.
CASES: dict[str, CaseDetail] = {}
SCANS: dict[str, ScanSummary] = {}


@router.post("/cases", response_model=CaseDetail)
def create_case(payload: CaseCreate):
    cid = str(uuid4())
    created_at = datetime.utcnow()

    scans: list[ScanSummary] = []
    for sc in payload.scans:
        sid = str(uuid4())
        scan = ScanSummary(
            id=sid,
            type=sc.type,
            target=sc.target,
            status="pending",
        )
        SCANS[sid] = scan
        scans.append(scan)

    case = CaseDetail(
        id=cid,
        case_id=payload.case_id,
        name=payload.name,
        assessed_by=payload.assessed_by,
        description=payload.description,
        created_at=created_at,
        last_scan_status=scans[-1].status if scans else None,
        scans=scans,
    )
    CASES[cid] = case
    return case


@router.get("/cases", response_model=list[CaseSummary])
def list_cases():
    return [
        CaseSummary(
            id=c.id,
            case_id=c.case_id,
            name=c.name,
            assessed_by=c.assessed_by,
            description=c.description,
            created_at=c.created_at,
            last_scan_status=c.last_scan_status,
        )
        for c in CASES.values()
    ]


@router.get("/cases/{case_id}", response_model=CaseDetail)
def get_case(case_id: str):
    case = CASES.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case
