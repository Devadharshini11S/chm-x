# app/api/routes_host.py
import socket
import subprocess
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/host", tags=["host"])

COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 8080]

SERVICE_MAP = {
    21: "ftp",
    22: "ssh",
    23: "telnet",
    25: "smtp",
    53: "dns",
    80: "http",
    110: "pop3",
    135: "msrpc",
    139: "netbios",
    143: "imap",
    443: "https",
    445: "smb",
    8080: "http-proxy",
}


def ping_host(host: str) -> bool:
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "1", host],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except Exception:
        return False


def scan_ports(host: str, ports: List[int]) -> List[dict]:
    open_ports = []
    for p in ports:
        try:
            s = socket.socket()
            s.settimeout(0.5)
            s.connect((host, p))
        except Exception:
            pass
        else:
            open_ports.append(
                {
                    "port": p,
                    "service": SERVICE_MAP.get(p, "unknown"),
                }
            )
        finally:
            s.close()
    return open_ports


@router.get("/scan")
def scan_host_api(
    host: str = Query(..., description="Hostname or IP to scan"),
    ports: Optional[str] = Query(
        None,
        description="Comma-separated list or range, e.g. '80,443,8080' or '1-1024'. "
                    "If empty, scan common ports."
    ),
):
    """
    Simple host scanner for CHM-X:
      - ping check
      - TCP connect scan on selected ports
    """
    if not host:
        raise HTTPException(status_code=400, detail="Host is required")

    # parse ports
    if ports:
        port_list: list[int] = []
        for part in ports.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-", 1)
                port_list.extend(range(int(start), int(end) + 1))
            else:
                port_list.append(int(part))
    else:
        port_list = COMMON_PORTS

    alive = ping_host(host)
    open_ports = scan_ports(host, port_list)

    return {
        "host": host,
        "alive": alive,
        "ports_scanned": len(port_list),
        "open_ports": open_ports,
    }
