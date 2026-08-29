"""
NetSage AI - FastAPI application entrypoint.

Run with:
    uvicorn main:app --reload
from inside the backend/ directory (see README.md for full setup).
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# main.py is designed to be run as `uvicorn main:app` from *inside* the
# backend/ directory (see README.md), but every module in this project
# uses absolute `from backend.xxx import ...` imports so that backend/
# rules/checker.py can also be invoked standalone as its own CLI. That
# means the project root (backend/'s parent) must be importable as a
# package root - this shim adds it before any `backend.*` import runs,
# regardless of the working directory uvicorn was launched from.
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_BACKEND_DIR, ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Load .env before anything else imports os.getenv("GEMINI_API_KEY").
load_dotenv()

from backend.api import cases, dashboard, diagnosis, practice, reviews, workspace  # noqa: E402

app = FastAPI(
    title="NetSage AI",
    description=(
        "AI-assisted network troubleshooting with mandatory human review. "
        "AI recommendations are suggestions and must be reviewed by a "
        "human before implementation."
    ),
    version="1.0.0",
)

# Permissive CORS for local development (Vite dev server on :5173, or a
# static build served elsewhere). Tighten this before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cases.router)
app.include_router(diagnosis.router)
app.include_router(reviews.router)
app.include_router(dashboard.router)
app.include_router(workspace.router)
app.include_router(practice.router)


@app.get("/")
def root():
    provider_key_present = bool(os.getenv("GEMINI_API_KEY", "").strip())
    return {
        "name": "NetSage AI",
        "description": "AI-assisted network troubleshooting with human review",
        "mock_mode": not provider_key_present,
        "safety_notice": (
            "AI recommendations are suggestions and must be reviewed by "
            "a human before implementation."
        ),
        "docs": "/docs",
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}
