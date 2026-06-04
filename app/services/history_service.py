import json
import os
from typing import Dict

BASELINE_PATH = "baseline.json"


def load_baseline() -> Dict[str, Dict[str, str]]:
    """
    Returns a dict like:
    {
      "/path/file": {"sha256": "...", "fuzzy": "..."},
      ...
    }
    """
    if not os.path.exists(BASELINE_PATH):
        return {}
    with open(BASELINE_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return {}
    return data


def save_baseline(store: Dict[str, Dict[str, str]]) -> None:
    with open(BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2)

