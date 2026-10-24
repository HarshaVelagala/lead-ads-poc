import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./leads.db")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "")
META_APP_SECRET = os.getenv("META_APP_SECRET", "")
META_PAGE_ID = os.getenv("META_PAGE_ID", "")
META_API_VERSION = os.getenv("META_API_VERSION", os.getenv("META_GRAPH_API_VERSION", "vXX.X"))
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8081,http://127.0.0.1:8081",
    ).split(",")
    if origin.strip()
]
