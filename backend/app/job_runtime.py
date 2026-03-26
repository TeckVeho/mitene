"""Shared async primitives for job execution (avoids circular imports)."""

import asyncio

from app.config import MAX_CONCURRENT_JOBS

job_semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)
