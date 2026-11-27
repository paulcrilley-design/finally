"""Uvicorn entry point: `uvicorn app.server:app`. Tests import app.main instead."""

from __future__ import annotations

import logging

from dotenv import load_dotenv

from app.main import PROJECT_ROOT, create_app

# Variables already set, including empty ones, win. A missing file is fine.
load_dotenv(PROJECT_ROOT / ".env", override=False)
logging.basicConfig(level=logging.INFO)  # uvicorn does not configure app loggers

app = create_app()
