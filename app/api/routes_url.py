# app/api/routes_url.py
from typing import Optional
from urllib.parse import urlparse

import requests
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/url", tags=["url"])


def is_url(value: str) -> bool:
    p = urlparse(value)
    return p.scheme in ("http", "https") and bool(p.netloc)


@router.get("/scan-basic")
def scan_url_basic(
    url: str = Query(..., description="Target URL"),
    timeout: int = Query(10, ge=1, le=60, description="Request timeout in seconds"),
):
    """
    Basic URL security check:
      - status, redirects, HTTPS vs HTTP
      - presence of key security headers
    """
    if not is_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL")

    try:
        resp = requests.get(url, timeout=timeout, allow_redirects=True)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Request failed: {e}")

    final_url = resp.url
    history = [r.status_code for r in resp.history]
    headers = resp.headers

    security_headers = {
        "Strict-Transport-Security": headers.get("Strict-Transport-Security"),
        "Content-Security-Policy": headers.get("Content-Security-Policy"),
        "X-Frame-Options": headers.get("X-Frame-Options"),
        "X-Content-Type-Options": headers.get("X-Content-Type-Options"),
        "Referrer-Policy": headers.get("Referrer-Policy"),
    }

    issues = []

    if final_url.startswith("http://"):
        issues.append("Site is not using HTTPS (final URL is http).")
    if not security_headers["Strict-Transport-Security"]:
        issues.append("Missing Strict-Transport-Security header.")
    if not security_headers["Content-Security-Policy"]:
        issues.append("Missing Content-Security-Policy header.")
    if not security_headers["X-Frame-Options"]:
        issues.append("Missing X-Frame-Options header.")
    if not security_headers["X-Content-Type-Options"]:
        issues.append("Missing X-Content-Type-Options header.")

    return {
        "target": url,
        "final_url": final_url,
        "status_code": resp.status_code,
        "redirect_chain": history,
        "security_headers": security_headers,
        "issues": issues,
    }


# ==============================
# NEW: advanced / deep scan
# ==============================
@router.get("/scan-advanced")
def scan_url_advanced(
    url: str = Query(..., description="Target URL"),
    timeout: int = Query(10, ge=1, le=60, description="Request timeout in seconds"),
):
    """
    Deep / active web scan (placeholder version).

    For now:
      - Reuse basic request.
      - Return a risk_score and structured sections (tls/headers/cookies/...)
      so the CLI 'web_scan_deep' can display something.

    You can later extend this with:
      - TLS analysis
      - extra header/cookie checks
      - light active payload tests
    """
    if not is_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL")

    try:
        resp = requests.get(url, timeout=timeout, allow_redirects=True)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Request failed: {e}")

    final_url = resp.url
    headers = resp.headers
    history = [r.status_code for r in resp.history]

    # Reuse some basic checks
    security_headers = {
        "Strict-Transport-Security": headers.get("Strict-Transport-Security"),
        "Content-Security-Policy": headers.get("Content-Security-Policy"),
        "X-Frame-Options": headers.get("X-Frame-Options"),
        "X-Content-Type-Options": headers.get("X-Content-Type-Options"),
        "Referrer-Policy": headers.get("Referrer-Policy"),
    }

    base_issues = []
    if str(final_url).startswith("http://"):
        base_issues.append("Site is not using HTTPS (final URL is http).")
    if not security_headers["Strict-Transport-Security"]:
        base_issues.append("Missing Strict-Transport-Security header.")
    if not security_headers["Content-Security-Policy"]:
        base_issues.append("Missing Content-Security-Policy header.")
    if not security_headers["X-Frame-Options"]:
        base_issues.append("Missing X-Frame-Options header.")
    if not security_headers["X-Content-Type-Options"]:
        base_issues.append("Missing X-Content-Type-Options header.")

    # Very simple risk score for now
    risk_score = min(len(base_issues) * 10, 100)

    # Structure for CLI deep output; you can enrich sections later
    tls_section = {
        "issues": [
            {
                "severity": "medium",
                "title": "HTTPS not enforced",
                "url": str(final_url),
                "evidence": "Final URL uses http instead of https.",
                "remediation": "Force HTTPS with redirects and HSTS.",
            }
        ]
        if str(final_url).startswith("http://")
        else []
    }

    headers_section = {
        "issues": [
            {
                "severity": "low" if name != "Content-Security-Policy" else "high",
                "title": f"Missing {name} header",
                "url": str(final_url),
                "evidence": f"{name} header not present in response.",
                "remediation": f"Add a secure {name} header.",
            }
            for name, val in security_headers.items()
            if not val
        ]
    }

    # Placeholder sections for now
    cookies_section = {"issues": []}
    auth_section = {"issues": []}
    inputs_section = {"issues": []}
    endpoints_section = {"issues": []}

    return {
        "target": url,
        "final_url": str(final_url),
        "status_code": resp.status_code,
        "redirect_chain": history,
        "risk_score": risk_score,
        "tls": tls_section,
        "headers": headers_section,
        "cookies": cookies_section,
        "auth": auth_section,
        "inputs": inputs_section,
        "endpoints": endpoints_section,
        "issues": base_issues,
    }
