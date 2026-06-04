# app/services/metadata_service.py

from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import json
import subprocess

import piexif
from PIL import Image

# Optional: C2PA support (run: pip install c2pa-python)
try:
    import c2pa
except ImportError:
    c2pa = None

# Known editors (mobile / desktop)
EDITOR_KEYWORDS: Dict[str, str] = {
    "picsart": "PicsArt",
    "canva": "Canva",
    "inshot": "InShot",
    "snapseed": "Snapseed",
    "lightroom": "Adobe Lightroom",
    "photoshop": "Adobe Photoshop",
    "pixlr": "Pixlr",
    "remini": "Remini",
    "capcut": "CapCut",
    "vsco": "VSCO",
    "gimp": "GIMP",
}

# Known AI generators (from Software / metadata strings)
AI_KEYWORDS: Dict[str, str] = {
    "midjourney": "Midjourney",
    "dall-e": "DALL·E",
    "dalle": "DALL·E",
    "stable diffusion": "Stable Diffusion",
    "sdxl": "Stable Diffusion XL",
    "flux": "Flux",
    "leonardo": "Leonardo AI",
    "copilot": "Microsoft Copilot",
    "firefly": "Adobe Firefly",
    "gemini": "Google Gemini",
    "chatgpt": "ChatGPT Image",
    "gpt-4o": "ChatGPT Image",
}


def _get_exif_dict(image_path: Path) -> Dict[str, Any]:
    try:
        img = Image.open(image_path)
        exif_bytes = img.info.get("exif")
        if not exif_bytes:
            return {}
        exif_dict = piexif.load(exif_bytes)
        return exif_dict
    except Exception:
        return {}


def _strip_nulls(value: Any) -> str:
    """
    Decode bytes, remove NUL padding and trim.
    """
    if isinstance(value, bytes):
        value = value.decode(errors="ignore")
    if isinstance(value, str):
        return value.replace("\x00", "").strip()
    return value or ""


def _detect_editor_and_ai(software: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Infer editing app and/or AI tool name from the Software string.
    Returns (edited_with, ai_tool).
    """
    if not software:
        return None, None

    s = software.lower()
    editor = None
    ai_tool = None

    for key, name in EDITOR_KEYWORDS.items():
        if key in s:
            editor = name
            break

    for key, name in AI_KEYWORDS.items():
        if key in s:
            ai_tool = name
            break

    return editor, ai_tool


def _detect_ai_from_c2pa(path: Path) -> Optional[str]:
    """
    Try to read a C2PA manifest and infer AI tool (e.g. OpenAI / ChatGPT).
    Requires c2pa-python; returns None if not available or no manifest.
    """
    if c2pa is None:
        return None

    try:
        with c2pa.c2pa.Reader(str(path)) as reader:
            manifest_store = json.loads(reader.json())
    except Exception:
        return None

    active_id = manifest_store.get("active_manifest")
    if not active_id:
        return None

    manifests = manifest_store.get("manifests", {})
    active = manifests.get(active_id, {})
    claim_gen = (active.get("claim_generator") or "").lower()

    if "openai" in claim_gen or "dall-e" in claim_gen or "chatgpt" in claim_gen or "gpt-4o" in claim_gen:
        return "OpenAI / ChatGPT"
    if "midjourney" in claim_gen:
        return "Midjourney"
    if "stable diffusion" in claim_gen:
        return "Stable Diffusion"

    return None


def _gps_to_degrees(value):
    """
    Convert EXIF GPS rational tuples to float degrees.
    """
    try:
        d = value[0][0] / value[0][1]
        m = value[1][0] / value[1][1]
        s = value[2][0] / value[2][1]
        return d + (m / 60.0) + (s / 3600.0)
    except Exception:
        return None


def _extract_gps_exif(gps_ifd: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract decimal latitude/longitude from EXIF GPS block (piexif dict).
    """
    if not gps_ifd:
        return None, None

    lat = lon = None

    lat_ref = gps_ifd.get(piexif.GPSIFD.GPSLatitudeRef)
    lat_val = gps_ifd.get(piexif.GPSIFD.GPSLatitude)
    lon_ref = gps_ifd.get(piexif.GPSIFD.GPSLongitudeRef)
    lon_val = gps_ifd.get(piexif.GPSIFD.GPSLongitude)

    if lat_ref and lat_val:
        lat = _gps_to_degrees(lat_val)
        if isinstance(lat_ref, bytes):
            lat_ref = lat_ref.decode(errors="ignore")
        if lat_ref in ("S", "s"):
            lat = -lat if lat is not None else None

    if lon_ref and lon_val:
        lon = _gps_to_degrees(lon_val)
        if isinstance(lon_ref, bytes):
            lon_ref = lon_ref.decode(errors="ignore")
        if lon_ref in ("W", "w"):
            lon = -lon if lon is not None else None

    return lat, lon


def _get_exiftool_tags(path: Path) -> Dict[str, Any]:
    """
    Call exiftool -j and return the first JSON object with all tags.
    Uses default keys (no group names) so it matches CLI output.[web:454][web:425]
    """
    try:
        out = subprocess.check_output(
            ["exiftool", "-j", str(path)],
            stderr=subprocess.DEVNULL,
        )
        data = json.loads(out)
        return data[0] if data else {}
    except Exception:
        return {}


def _pick_first(et: Dict[str, Any], keys: list[str]) -> Optional[str]:
    for k in keys:
        if k in et:
            v = _strip_nulls(et.get(k))
            if v:
                return v
    return None


def _pick_datetime(et: Dict[str, Any]) -> Optional[str]:
    """
    Choose the best datetime string from ExifTool tags.[web:454]
    """
    candidates = [
        "Date/Time Original",
        "Create Date",
        "DateTimeOriginal",
        "CreateDate",
        "Modify Date",
        "FileModifyDate",
    ]
    for k in candidates:
        if k in et:
            return _strip_nulls(et.get(k))
    return None


def extract_clean_metadata(file_path: str) -> Dict[str, Any]:
    """
    Returns a small dict:
    {
      make, model, software, datetime,
      width, height, has_gps,
      gps_lat, gps_lon,
      edited_with, ai_tool
    }
    """
    path = Path(file_path)

    # -------- image size --------
    width = height = None
    try:
        with Image.open(path) as img:
            width, height = img.size
    except Exception:
        pass

    # -------- ExifTool tags (primary source) --------
    et = _get_exiftool_tags(path)

    # Keys chosen to match what you see in your exiftool output sample
    make = _pick_first(et, ["Make"])
    model = _pick_first(et, ["Camera Model Name", "CameraModelName", "Model"])
    software = _pick_first(et, ["Software"])

    dt_str = _pick_datetime(et)

    # -------- GPS detection --------
    # ExifTool (without -n) gives strings like "50 deg 52' 17.00\" N";
    # we already have reliable numeric GPS from piexif, so skip parsing strings here.
    gps_lat = gps_lon = None
    has_gps = False

    exif = _get_exif_dict(path)
    gps_ifd = exif.get("GPS", {})
    gps_lat, gps_lon = _extract_gps_exif(gps_ifd)
    has_gps = gps_lat is not None and gps_lon is not None

    # -------- editor / AI from Software + C2PA --------
    edited_with, ai_tool = _detect_editor_and_ai(software)
    ai_from_c2pa = _detect_ai_from_c2pa(path)
    if ai_from_c2pa and not ai_tool:
        ai_tool = ai_from_c2pa

    clean = {
        "make": make,
        "model": model,
        "software": software,
        "datetime": dt_str,
        "width": width,
        "height": height,
        "has_gps": bool(has_gps),
        "gps_lat": gps_lat,
        "gps_lon": gps_lon,
        # place is left None here; you can resolve via reverse geocoding if needed
        "gps_place": None,
        "edited_with": edited_with,
        "ai_tool": ai_tool,
    }

    return clean
