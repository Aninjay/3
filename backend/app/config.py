import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Config:
    IS_VERCEL = os.environ.get("VERCEL", "").strip().lower() in {"1", "true", "yes"}
    IS_PRODUCTION = os.environ.get("FLASK_ENV", "development").strip().lower() == "production" or IS_VERCEL

    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        if IS_PRODUCTION:
            raise RuntimeError("SECRET_KEY must be set for production and Vercel deployments.")
        SECRET_KEY = "tapmi-cultural-committee-dev-secret-key-2026"

    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        if IS_PRODUCTION:
            raise RuntimeError("DATABASE_URL must point to the persistent PostgreSQL database in production.")
        DATABASE_URL = f"sqlite:///{BASE_DIR / 'backend' / 'cultural_committee.db'}"
    if IS_PRODUCTION and not DATABASE_URL.startswith(("postgres://", "postgresql://")):
        raise RuntimeError("Production and Vercel deployments require DATABASE_URL to use PostgreSQL.")

    OTP_DELIVERY_MODE = os.environ.get("OTP_DELIVERY_MODE", "development")
    OTP_EXPIRY_MINUTES = int(os.environ.get("OTP_EXPIRY_MINUTES", "15"))
    OTP_MAX_ATTEMPTS = int(os.environ.get("OTP_MAX_ATTEMPTS", "5"))
    PILOT_EVENT_NAME = os.environ.get("PILOT_EVENT_NAME", "Kala Fest")
    VOLUNTEER_LOGIN_EMAIL = "volunteer@tapmi.edu.in"
    CORE_COMMITTEE_LOGIN_EMAIL = "core@tapmi.edu.in"
    DATA_DIR = BASE_DIR
    cors_default = "" if IS_PRODUCTION else "*"
    CORS_ORIGINS = [origin.strip() for origin in os.environ.get("CORS_ORIGINS", cors_default).split(",") if origin.strip()]
    if IS_PRODUCTION and not CORS_ORIGINS:
        raise RuntimeError("CORS_ORIGINS must list the trusted frontend origin in production.")
    if IS_PRODUCTION and "*" in CORS_ORIGINS:
        raise RuntimeError("CORS_ORIGINS cannot use a wildcard in production.")
