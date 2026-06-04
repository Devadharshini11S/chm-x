# app/services/scanner_service.py

import os
import time
import uuid
from collections import Counter
from datetime import datetime
from typing import List, Optional, Dict, Any

import ssdeep
from sqlalchemy.orm import Session

from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing

from app.core.db import SessionLocal
from app.core.models import (
    Case,
    Scan,
    ScanFile,
    ScanSummary,
    ScanResponse,
    MatchItem,
)
from app.services.hashing_service import (
    compute_sha256,
    compute_fuzzy_hash,
    compute_improved_fuzzy_hash,
    get_file_type,
    get_file_times,
    extract_exif_metadata,
)
from app.services.baseline_store import get_baseline, upsert_baseline
from app.services.metadata_service import extract_clean_metadata
from app.services.origin_classifier import classify_origin

from PIL import Image
import imagehash
import csv

# NEW: exiftool + metadata fuzzy hashing
import subprocess
import json

# tuning knobs
MAX_WORKERS = min(8, multiprocessing.cpu_count())  # parallel hashing
CROSS_SIM_MAX_FILES = 2000  # skip cross-file similarity if more than this
EXIFTOOL_PATH = "exiftool"  # adjust path if needed


def exiftool_json(path: str) -> Dict[str, Any]:
    """
    Call exiftool for a single file and return all tags as a dict.
    Uses complete ExifTool capabilities via -j -G1 -a -n.
    """
    try:
        cmd = [EXIFTOOL_PATH, "-j", "-G1", "-a", "-n", path]
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            return {}
        data = json.loads(res.stdout)
        return data[0] if data else {}
    except Exception:
        return {}


def canonical_metadata_string(meta: Dict[str, Any]) -> str:
    """
    Build a deterministic string from all ExifTool tags for metadata hashing.
    """
    parts = []
    for key in sorted(meta.keys()):
        val = meta[key]
        parts.append(f"{key}={val}")
    return "\n".join(parts)


def metadata_ssdeep(meta: Dict[str, Any]) -> str:
    """
    Compute ssdeep fuzzy hash over the canonical metadata string.
    """
    canon = canonical_metadata_string(meta)
    return ssdeep.hash(canon)


def bucket_from_score(score: float) -> str:
    if score >= 90:
        return "high"
    elif score >= 60:
        return "medium"
    else:
        return "low"


def risk_from_score(score: float) -> str:
    if score >= 99:
        return "ok"
    elif score >= 80:
        return "suspicious_modified"
    else:
        return "changed"


def compute_similarity(fuzzy_new: str, fuzzy_old: str) -> float:
    if not fuzzy_old:
        return 0.0
    return float(ssdeep.compare(fuzzy_new, fuzzy_old))


def compute_phash(path: str) -> Optional[str]:
    try:
        with Image.open(path) as img:
            return str(imagehash.phash(img))
    except Exception:
        return None


def phash_distance(h1: Optional[str], h2: Optional[str]) -> Optional[int]:
    if not h1 or not h2:
        return None
    try:
        return imagehash.hex_to_hash(h1) - imagehash.hex_to_hash(h2)
    except Exception:
        return None


def export_scan_to_csv(scan_id: str, matches: List[MatchItem], out_path: str):
    """
    Export per-file results to a CSV file in a human-friendly shape.
    One row = one file.
    """
    fieldnames = [
        "scan_id",
        "file_path",
        "type",
        "status",
        "risk",
        "score",
        "sha256",
        "sha256_prev",
        "ssdeep",
        "ssdeep_prev",
        "phash",
        "origin",
        # optional: "meta_ssdeep" if you want it in CSV
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for m in matches:
            writer.writerow({
                "scan_id": scan_id,
                "file_path": m.file_path,
                "type": m.file_type or "",
                "status": m.status or "",
                "risk": m.risk_level or "",
                "score": f"{m.score:.1f}",
                "sha256": m.sha_new or "",
                "sha256_prev": m.sha_old or "",
                "ssdeep": m.fuzzy_new or "",
                "ssdeep_prev": m.fuzzy_old or "",
                "phash": m.phash or "",
                "origin": m.origin_guess or "",
            })


def scan_path(
    root_path: str,
    case_id: Optional[str] = None,
    assessed_by: Optional[str] = None,
    mode: str = "monitor",
    scan_type: str = "full_evidence",
) -> ScanResponse:
    db: Session = SessionLocal()
    try:
        case = None
        if case_id:
            case = db.query(Case).filter(Case.id == case_id).first()
            if not case:
                case = Case(
                    id=case_id,
                    name=f"Case {case_id}",
                    description="",
                    assessed_by=assessed_by,
                )
                db.add(case)
                db.commit()
                db.refresh(case)

        scan_id = str(uuid.uuid4())
        scan = Scan(
            id=scan_id,
            case_id=case.id if case else None,
            root_path=root_path,
            mode=mode,
            status="queued",
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)

        started_at = datetime.utcnow()
        start_ts = time.time()

        matches: List[MatchItem] = []
        scan_files: List[ScanFile] = []

        file_types_counter = Counter()
        score_buckets_counter = Counter()

        new_files = 0
        modified_files = 0

        # 1) collect all paths first (single os.walk)
        all_paths: List[str] = []
        for dirpath, _, filenames in os.walk(root_path):
            for name in filenames:
                full_path = os.path.join(dirpath, name)
                all_paths.append(full_path)

        total_files = len(all_paths)

        # 2) per-file worker
        def process_one(path: str):
            nonlocal new_files, modified_files

            file_type = get_file_type(path)
            file_types_counter[file_type] += 1

            # --- HASHES (CONTENT) ---
            sha_new = compute_sha256(path)
            fuzzy_new = compute_fuzzy_hash(path)

            try:
                fuzzy_improved = compute_improved_fuzzy_hash(path)
                print("IMPROVED FUZZY:", fuzzy_improved, "PATH:", path)
            except Exception:
                fuzzy_improved = ""

            mtime, ctime, atime = get_file_times(path)
            timestamp = mtime

            phash_new = None
            if file_type == "image":
                phash_new = compute_phash(path)

            baseline = get_baseline(path)

            sha_old = ""
            fuzzy_old = ""
            phash_old = None

            sha_initial = None
            fuzzy_initial = None
            phash_initial = None

            score = 0.0
            status = "new"
            risk_level = "changed"

            if baseline is None:
                new_files += 1
            else:
                sha_initial = baseline.initial.sha256
                fuzzy_initial = baseline.initial.fuzzy
                phash_initial = baseline.initial.phash

                sha_old = baseline.last.sha256
                fuzzy_old = baseline.last.fuzzy
                phash_old = baseline.last.phash

                if sha_new == sha_old:
                    score = 100.0
                    status = "intact"
                else:
                    score = compute_similarity(fuzzy_new, fuzzy_old)
                    status = "modified"
                    modified_files += 1

                risk_level = risk_from_score(score)

            # ---------- METADATA / EXIFTOOL ----------
            exif: Dict[str, Any] = {}
            meta_full: Dict[str, Any] = {}
            meta_sig: Optional[str] = None

            author: Optional[str] = None
            exif_datetime: Optional[str] = None
            clean_md: dict = {}
            origin_guess: Optional[str] = None
            has_gps_flag = False
            gps_lat: Optional[float] = None
            gps_lon: Optional[float] = None
            gps_place: Optional[str] = None

            if file_type == "image" and scan_type in (
                "metadata",
                "ai_detection",
                "full_evidence",
            ):
                # full ExifTool metadata
                meta_full = exiftool_json(path) or {}

                # existing lightweight EXIF helper
                exif = extract_exif_metadata(path) or {}
                author = exif.get("author")
                exif_datetime = exif.get("datetime_original") or exif.get("datetime")

                clean_md = extract_clean_metadata(path) or {}
                origin_guess = classify_origin(clean_md)
                has_gps_flag = bool(clean_md.get("has_gps"))

                gps_lat = clean_md.get("gps_lat") or clean_md.get("lat")
                gps_lon = clean_md.get("gps_lon") or clean_md.get("lon")
                gps_place = clean_md.get("gps_place") or clean_md.get("place")

                # metadata fuzzy hash over canonical ExifTool tags
                if meta_full:
                    meta_sig = metadata_ssdeep(meta_full)
                    # embed into clean_md so CLI/CSV can access it
                    clean_md = dict(clean_md)
                    clean_md["meta_ssdeep"] = meta_sig

            scan_file = ScanFile(
                scan_id=scan.id,
                file_path=path,
                size_bytes=os.path.getsize(path),
                mtime=mtime,
                ctime=ctime,
                atime=atime,
                mime_type=file_type,
                author=author,
                exif_datetime=exif_datetime,
                clean_metadata=clean_md if clean_md else None,
                has_gps=has_gps_flag,
                origin_guess=origin_guess,
                sha_new=sha_new,
                sha_old=sha_old,
                fuzzy_new=fuzzy_new,
                fuzzy_old=fuzzy_old,
                similarity_score=score,
                status=status,
                risk_level=risk_level,
                is_baseline_match=(status == "intact"),
                phash=phash_new,
                gps_lat=gps_lat,
                gps_lon=gps_lon,
                gps_place=gps_place,
                top_matches=None,
                meta_full=meta_full if meta_full else None,  # NEW
            )

            match = MatchItem(
                id=str(uuid.uuid4()),
                file_path=path,
                file_type=file_type,
                sha_new=sha_new,
                sha_old=sha_old,
                fuzzy_new=fuzzy_new,
                fuzzy_old=fuzzy_old,
                score=score,
                status=status,
                risk_level=risk_level,
                timestamp=timestamp,
                phash=phash_new,
                phash_old=phash_old,
                sha_initial=sha_initial,
                fuzzy_initial=fuzzy_initial,
                phash_initial=phash_initial,
                clean_metadata=clean_md or None,
                origin_guess=origin_guess,
                has_gps=has_gps_flag,
                gps_lat=gps_lat,
                gps_lon=gps_lon,
                gps_place=gps_place,
                top_matches=None,
            )

            bucket = bucket_from_score(score)
            score_buckets_counter[bucket] += 1

            # do NOT update baseline here (not thread‑safe)
            baseline_info = (path, sha_new, fuzzy_new, phash_new)

            return scan_file, match, baseline_info

        # 3) run hashing+metadata in parallel
        baseline_updates = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futures = {ex.submit(process_one, p): p for p in all_paths}
            for fut in as_completed(futures):
                scan_file, match, baseline_info = fut.result()
                scan_files.append(scan_file)
                matches.append(match)
                baseline_updates.append(baseline_info)
                db.add(scan_file)

        # commit all files together
        db.commit()

        # 4) baseline updates in main thread (safe)
        for path, sha_new, fuzzy_new, phash_new in baseline_updates:
            upsert_baseline(path, sha_new, fuzzy_new, phash_new)

        # ---------- cross-file ssdeep + phash similarity ----------
        n = len(matches)
        if n <= CROSS_SIM_MAX_FILES:
            for i in range(n):
                base = matches[i]
                base_file = scan_files[i]
                sims: List[Dict[str, Any]] = []

                if base.fuzzy_new:
                    for j in range(n):
                        if i == j:
                            continue
                        other = matches[j]
                        if not other.fuzzy_new:
                            continue
                        sim = float(ssdeep.compare(base.fuzzy_new, other.fuzzy_new))
                        if sim > 0:
                            sims.append(
                                {
                                    "path": other.file_path,
                                    "similarity": float(sim),
                                    "type": "ssdeep",
                                }
                            )

                if base.phash:
                    for j in range(n):
                        if i == j:
                            continue
                        other = matches[j]
                        if not other.phash:
                           	continue

                        dist = phash_distance(base.phash, other.phash)
                        if dist is None:
                            continue

                        if dist <= 10:
                            d = int(dist)
                            visual_sim = float(max(0, 100 - d * 4))
                            sims.append(
                                {
                                    "path": other.file_path,
                                    "similarity": visual_sim,
                                    "phash_distance": d,
                                    "type": "phash",
                                }
                            )

                sims.sort(key=lambda x: x["similarity"], reverse=True)
                top = sims[:3] if sims else []

                base.top_matches = top
                base_file.top_matches = top
        else:
            print(f"Skipping cross-file similarity for {n} files (limit {CROSS_SIM_MAX_FILES}).")

        finished_at = datetime.utcnow()
        scan_time_ms = int((time.time() - start_ts) * 1000)

        scan.status = "done"
        scan.started_at = started_at
        scan.finished_at = finished_at
        scan.total_files = total_files
        scan.new_files = new_files
        scan.modified_files = modified_files
        db.commit()

        summary = ScanSummary(
            scan_id=scan.id,
            started_at=started_at,
            finished_at=finished_at,
            total_files=total_files,
            total_matches=len(matches),
            scan_time_ms=scan_time_ms,
            file_types=dict(file_types_counter),
            score_buckets=dict(score_buckets_counter),
        )

        # --------- EXPORT TO CSV IN PER-CASE FOLDER ----------
        base_output_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "output")
        )
        case_folder = case.id if case else "default"
        out_dir = os.path.join(base_output_dir, case_folder)
        os.makedirs(out_dir, exist_ok=True)

        out_csv = os.path.join(out_dir, f"{scan.id}.csv")
        export_scan_to_csv(scan.id, matches, out_csv)
        print("EXPORTED CSV:", out_csv)

        return ScanResponse(summary=summary, matches=matches)
    finally:
        db.close()
