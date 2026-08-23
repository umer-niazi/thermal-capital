"""FastAPI application entry point for Thermal Capital."""

from __future__ import annotations

import os
import pathlib
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")
from backend.api.router import router as api_router

FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"

app = FastAPI(
    title="Thermal Capital API",
    description="Municipal capital planning and decision-support platform for urban heat mitigation.",
    version="1.0.0",
)

# Configure CORS: support local dev + Vercel deployment domains + optional ALLOWED_ORIGINS env
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS")
if allowed_origins_env:
    allowed_origins = [orig.strip() for orig in allowed_origins_env.split(",") if orig.strip()]
elif os.environ.get("VERCEL"):
    allowed_origins = []
else:
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else [],
    allow_origin_regex=r"^https://.*\.vercel\.app$" if (os.environ.get("VERCEL") or not allowed_origins) else None,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
)

# Include API endpoints
app.include_router(api_router)

# Mount frontend build if present
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
