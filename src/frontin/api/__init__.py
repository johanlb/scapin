"""
Scapin API Module

FastAPI-based REST API for Scapin cognitive guardian.
Exposes all CLI functionality via HTTP endpoints.
"""

from src.frontin.api.app import create_app

__all__ = ["create_app"]
