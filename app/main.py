# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_scan import router as scan_router
from app.api.routes_host import router as host_router
from app.api.routes_url import router as url_router
from app.api.routes_cases import router as cases_router
from app.api.routes_scans import router as scans_router
from app.core.models import init_db

app = FastAPI(
    title="CHM-X Backend",
    version="1.0.0",
)

# CORS (for your React / web frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    # initialize database / models
    init_db()


@app.get("/")
def root():
    return {"message": "CHM-X backend running"}


@app.get("/health")
def health():
    return {"status": "ok"}


# Filesystem / evidence scan routes
app.include_router(scan_router)

# Host / port scan routes
#app.include_router(host_router)

# URL scan routes (basic + deep)
#app.include_router(url_router)

# Case management routes (for the New Case wizard, etc.)
app.include_router(cases_router, prefix="/api", tags=["cases"])

# Scan metadata/report routes used by frontend + CLI show_metadata
app.include_router(scans_router, prefix="/api", tags=["scans"])
