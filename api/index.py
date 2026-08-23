"""Vercel Serverless Function entrypoint for Thermal Capital FastAPI backend."""

from __future__ import annotations

import sys
import pathlib

# Ensure the repository root is on sys.path so backend and fortyguard modules resolve correctly
ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.main import app
