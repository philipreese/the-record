import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Adjust path to import backend modules
APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(APP_DIR))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

_log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
_log_handler = logging.StreamHandler()
_log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
_app_logger = logging.getLogger("app")
_app_logger.setLevel(_log_level)
_app_logger.handlers = [_log_handler]
_app_logger.propagate = False  # Alembic's fileConfig sets root to WARN; bypass it

sys.path.append(PROJECT_ROOT)

from app.db import bootstrap_db_from_json
from app.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Ensure database schema exists and bootstrap initial data on startup."""
    bootstrap_db_from_json()
    yield

app = FastAPI(title="The Record API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes under the /api prefix
app.include_router(router, prefix="/api")
