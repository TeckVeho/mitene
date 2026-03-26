"""Backward-compatible re-export of the external API v1 router."""
from app.routers.v1 import register_store_functions, router

__all__ = ["router", "register_store_functions"]
