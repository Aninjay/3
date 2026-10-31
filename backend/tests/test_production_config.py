import os
import subprocess
import sys


def load_config_with(overrides):
    env = os.environ.copy()
    for key in ("DATABASE_URL", "SECRET_KEY", "FLASK_ENV", "VERCEL", "CORS_ORIGINS"):
        env.pop(key, None)
    env.update(overrides)
    return subprocess.run(
        [sys.executable, "-c", "from backend.app.config import Config; print(Config.DATABASE_URL)"],
        capture_output=True,
        text=True,
        env=env,
    )


def test_vercel_config_fails_closed_without_production_database():
    result = load_config_with({
        "VERCEL": "1",
        "SECRET_KEY": "test-secret",
        "CORS_ORIGINS": "https://frontend.example",
    })

    assert result.returncode != 0
    assert "DATABASE_URL must point to the persistent PostgreSQL database" in result.stderr


def test_production_config_rejects_wildcard_cors():
    result = load_config_with({
        "FLASK_ENV": "production",
        "SECRET_KEY": "test-secret",
        "DATABASE_URL": "postgresql://user:password@localhost/database",
        "CORS_ORIGINS": "*",
    })

    assert result.returncode != 0
    assert "CORS_ORIGINS cannot use a wildcard" in result.stderr


def test_vercel_config_accepts_explicit_postgres_and_frontend_origin():
    result = load_config_with({
        "VERCEL": "1",
        "FLASK_ENV": "production",
        "SECRET_KEY": "test-secret",
        "DATABASE_URL": "postgresql://user:password@localhost/database",
        "CORS_ORIGINS": "https://frontend.example",
    })

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().startswith("postgresql://")
