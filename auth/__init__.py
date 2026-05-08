"""
Layer 1 — Authentication
OAuth2 flow and token management for Polar AccessLink API.

Public API:
    get_token() -> str: Returns stored access token
    get_user_id() -> str: Returns stored Polar user ID
"""

from auth.polar_auth import get_token, get_user_id

__all__ = ["get_token", "get_user_id"]
