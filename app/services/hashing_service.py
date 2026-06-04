# app/services/hashing_service.py
import hashlib
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Tuple, Dict, Any

import ssdeep
from PIL import Image, ExifTags  # Pillow


# ---------- Existing helpers ----------

def compute_sha256(path: str) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def compute_fuzzy_hash(path: str) -> str:
    """
    Standard ssdeep fuzzy hash (file-level).
    """
    return ssdeep.hash_from_file(path)


def get_file_type(path: str) -> str:
    name = os.path.basename(path).lower()
    # include TIFF as image
    if name.endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff")):
        return "image"
    elif name.endswith((".exe", ".dll", ".so")):
        return "executable"
    elif name.endswith((".zip", ".rar", ".7z", ".tar", ".gz")):
        return "archive"
    elif name.endswith((".pdf", ".doc", ".docx", ".txt")):
        return "document"
    else:
        return "other"


def get_file_times(path: str):
    st = os.stat(path)
    mtime = datetime.fromtimestamp(st.st_mtime)
    ctime = datetime.fromtimestamp(st.st_ctime)
    atime = datetime.fromtimestamp(st.st_atime)
    return mtime, ctime, atime


def extract_exif_metadata(path: str) -> Dict[str, Any]:
    """
    Extract simple EXIF metadata from images:
    - datetime_original / datetime
    - author (Artist)
    Returns {} if no EXIF or not an image.
    """
    try:
        img = Image.open(path)
        exif = img.getexif()
        if not exif:
            return {}

        labeled = {}
        for tag_id, value in exif.items():
            tag_name = ExifTags.TAGS.get(tag_id, tag_id)
            labeled[tag_name] = value

        result: Dict[str, Any] = {}

        if "DateTimeOriginal" in labeled:
            result["datetime_original"] = str(labeled["DateTimeOriginal"])
        elif "DateTime" in labeled:
            result["datetime"] = str(labeled["DateTime"])

        if "Artist" in labeled:
            result["author"] = str(labeled["Artist"])

        return result
    except Exception:
        return {}


# ---------- NEW: improved ssdeep via ssdeeper ----------

SSDEEPER_BIN = "/usr/bin/ssdeep"  # adjust if installed somewhere else, e.g. "/usr/local/bin/ssdeeper"


def compute_improved_fuzzy_hash(path: str) -> str:
    """
    Compute the improved ssdeep-style fuzzy hash using the ssdeeper binary.

    This uses the modified implementation from the 'ssdeeper' project
    (bugfixes and parameter changes as described in the paper). [file:17]
    """
    file_path = str(Path(path))
    try:
        result = subprocess.run(
            [SSDEEPER_BIN, file_path],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        # You may want to log this properly in your app
        raise RuntimeError("ssdeeper binary not found. Check SSDEEPER_BIN path.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ssdeeper failed for {file_path}: {e.stderr.strip()}")

    stdout = result.stdout.strip()
    if not stdout:
        raise RuntimeError(f"Empty output from ssdeeper for {file_path}")

    # Adjust parsing to actual ssdeeper output format.
    # Most tools output "<hash>  <filename>" per line; take the last line.
    last_line = stdout.splitlines()[-1]
    parts = last_line.split()
    if not parts:
        raise RuntimeError(f"Could not parse ssdeeper output for {file_path}: {last_line!r}")

    fuzzy_improved = parts[0]
    return fuzzy_improved


# ---------- High-level helper to compute all hashes ----------

def compute_all_hashes(path: str) -> Dict[str, Any]:
    """
    Compute:
    - sha256
    - standard ssdeep fuzzy hash
    - improved ssdeep fuzzy hash (ssdeeper)
    - file type
    - basic timestamps
    - EXIF metadata for images
    """
    sha256_value = compute_sha256(path)
    fuzzy_normal = compute_fuzzy_hash(path)

    try:
        fuzzy_improved = compute_improved_fuzzy_hash(path)
    except Exception:
        # If improved hashing fails, you can decide:
        # - set to empty string
        # - or re-raise
        fuzzy_improved = ""

    file_type = get_file_type(path)
    mtime, ctime, atime = get_file_times(path)
    exif_meta = extract_exif_metadata(path) if file_type == "image" else {}

    return {
        "path": path,
        "sha256": sha256_value,
        "fuzzy_normal": fuzzy_normal,
        "fuzzy_improved": fuzzy_improved,
        "file_type": file_type,
        "mtime": mtime.isoformat(),
        "ctime": ctime.isoformat(),
        "atime": atime.isoformat(),
        "exif": exif_meta,
    }
