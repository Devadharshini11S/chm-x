# app/services/matcher.py
from dataclasses import dataclass
from typing import Optional


@dataclass
class BaselineEntry:
    sha256: str
    fuzzy: str
    risk_level: str  # e.g. "ok", "suspicious_modified", "bad"


# Example baseline; fill with real data later
BASELINE = {
    # "07a617d1...": BaselineEntry(sha256="07a617d1...", fuzzy="3072:...", risk_level="ok"),
}


def classify_hashes(
    file_sha: str,
    file_fuzzy: str,
) -> Optional[tuple[str, str, float, str]]:
    """
    Returns (sha_old, fuzzy_old, score, risk_level) if matched, else None.
    """
    entry = BASELINE.get(file_sha)
    if entry:
        # Treat as exact match with score 100
        return entry.sha256, entry.fuzzy, 100.0, entry.risk_level

    # TODO: fuzzy-similarity logic using file_fuzzy vs baseline
    return None
