"""FastAPI application entry point for Thermal Capital."""

from __future__ import annotations

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

# Enable CORS for local development (Vite dev server on port 5173 / 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
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
