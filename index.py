"""Vercel's Python runtime entry point for the existing Flask API."""

from backend.app import create_app

app = create_app()
