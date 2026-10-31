import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        if os.environ.get("FLASK_ENV", "development").lower() == "production":
            raise RuntimeError("SECRET_KEY must be set in production.")
        SECRET_KEY = "tapmi-cultural-committee-dev-secret-key-2026"
    DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'backend' / 'cultural_committee.db'}")
    OTP_DELIVERY_MODE = os.environ.get("OTP_DELIVERY_MODE", "development")
    OTP_EXPIRY_MINUTES = int(os.environ.get("OTP_EXPIRY_MINUTES", "15"))
    OTP_MAX_ATTEMPTS = int(os.environ.get("OTP_MAX_ATTEMPTS", "5"))
    PILOT_EVENT_NAME = os.environ.get("PILOT_EVENT_NAME", "Kala Fest")
    VOLUNTEER_LOGIN_EMAIL = "volunteer@tapmi.edu.in"
    CORE_COMMITTEE_LOGIN_EMAIL = "core@tapmi.edu.in"
    DATA_DIR = BASE_DIR
    cors_default = "" if os.environ.get("FLASK_ENV", "development").lower() == "production" else "*"
    CORS_ORIGINS = [origin.strip() for origin in os.environ.get("CORS_ORIGINS", cors_default).split(",") if origin.strip()]
