# app/services/baseline_store.py

import json
import os
from dataclasses import dataclass
from typing import Optional, Dict, Any

BASELINE_FILE = "baseline.json"


@dataclass
class BaselineSnapshot:
    sha256: str
    fuzzy: str
    phash: Optional[str] = None


@dataclass
class BaselineEntry:
    """
    initial: first time the file was seen (fixed, never overwritten)
    last:    last scan's state (updated every scan)
    """
    initial: BaselineSnapshot
    last: BaselineSnapshot


def _load_all() -> Dict[str, Any]:
    if not os.path.exists(BASELINE_FILE):
        return {}
    with open(BASELINE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_all(data: Dict[str, Any]):
    with open(BASELINE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


def get_baseline(path: str) -> Optional[BaselineEntry]:
    """
    Returns None if file has never been seen.
    Otherwise returns BaselineEntry(initial=..., last=...).
    """
    data = _load_all()
    entry = data.get(path)
    if not entry:
        return None

    # Backward compatibility with old format:
    # {
    #   "sha256": "...",
    #   "fuzzy": "...",
    #   "phash": "..."
    # }
    if "initial" not in entry:
        snap = BaselineSnapshot(
            sha256=entry["sha256"],
            fuzzy=entry["fuzzy"],
            phash=entry.get("phash"),
        )
        return BaselineEntry(initial=snap, last=snap)

    init_raw = entry["initial"]
    last_raw = entry["last"]

    initial = BaselineSnapshot(
        sha256=init_raw["sha256"],
        fuzzy=init_raw["fuzzy"],
        phash=init_raw.get("phash"),
    )
    last = BaselineSnapshot(
        sha256=last_raw["sha256"],
        fuzzy=last_raw["fuzzy"],
        phash=last_raw.get("phash"),
    )
    return BaselineEntry(initial=initial, last=last)


def upsert_baseline(path: str, sha256: str, fuzzy: str, phash: Optional[str] = None):
    """
    Update baseline for this file:

    - If file is new:
        initial = last = current values
    - If file exists:
        initial stays the same
        last is updated to current values
    """
    data = _load_all()
    existing = data.get(path)

    if not existing or "initial" not in existing:
        # first time: create both initial and last
        snapshot = {
            "sha256": sha256,
            "fuzzy": fuzzy,
            "phash": phash,
        }
        data[path] = {
            "initial": snapshot,
            "last": snapshot,
        }
    else:
        # keep initial unchanged, only update last
        initial = existing["initial"]
        data[path] = {
            "initial": initial,
            "last": {
                "sha256": sha256,
                "fuzzy": fuzzy,
                "phash": phash,
            },
        }

    _save_all(data)
