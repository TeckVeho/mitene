"""
Backward-compatible entry point for the data layer.

Implementation is split under ``app.db`` (connection, jobs, videos, …).
"""
from app.db import *  # noqa: F403
