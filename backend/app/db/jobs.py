"""Job store CRUD."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

from . import connection
from .connection import _USE_MYSQL, _now, _row_to_dict, _store, _store_lock

# ---------------------------------------------------------------------------
# Jobs CRUD
# ---------------------------------------------------------------------------


async def store_create(job: dict) -> dict:
    if not _USE_MYSQL:
        async with _store_lock:
            _store[job["id"]] = dict(job)
        return dict(job)

    source_names = job.get("csvFileNames") or job.get("sourceFileNames", "")

    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO jobs (
                    id, job_type, source_file_names, notebook_title, instructions,
                    style, format, language, timeout,
                    status, steps, current_step, error_message, callback_url,
                    created_at, updated_at, completed_at
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s
                )
                """,
                (
                    job["id"],
                    job.get("jobType", "video"),
                    source_names,
                    job["notebookTitle"],
                    job["instructions"],
                    job.get("style"),
                    job.get("format"),
                    job.get("language"),
                    job.get("timeout"),
                    job.get("status", "pending"),
                    json.dumps(job.get("steps", []), ensure_ascii=False),
                    job.get("currentStep"),
                    job.get("errorMessage"),
                    job.get("callbackUrl"),
                    job["createdAt"],
                    job["updatedAt"],
                    job.get("completedAt"),
                ),
            )
    return job


async def store_get(job_id: str) -> dict:
    if not _USE_MYSQL:
        async with _store_lock:
            if job_id not in _store:
                from fastapi import HTTPException

                raise HTTPException(
                    status_code=404, detail=f"ジョブが見つかりません: {job_id}"
                )
            return dict(_store[job_id])

    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
            row = await cur.fetchone()

    if row is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404, detail=f"ジョブが見つかりません: {job_id}"
        )
    return _row_to_dict(row)


async def store_list(status: Optional[str] = None, job_type: Optional[str] = None) -> list[dict]:
    if not _USE_MYSQL:
        async with _store_lock:
            jobs = list(_store.values())
        jobs.sort(key=lambda j: j.get("createdAt", ""), reverse=True)
        if status and status != "all":
            jobs = [j for j in jobs if j["status"] == status]
        if job_type and job_type != "all":
            jobs = [j for j in jobs if j.get("jobType", "video") == job_type]
        return jobs

    conditions: list[str] = []
    params: list = []
    if status and status != "all":
        conditions.append("status = %s")
        params.append(status)
    if job_type and job_type != "all":
        conditions.append("job_type = %s")
        params.append(job_type)

    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            await cur.execute(
                f"SELECT * FROM jobs {where} ORDER BY created_at DESC",
                params,
            )
            rows = await cur.fetchall()

    return [_row_to_dict(r) for r in rows]


async def store_update(job_id: str, **kwargs) -> dict:
    if not _USE_MYSQL:
        async with _store_lock:
            if job_id not in _store:
                raise KeyError(f"ジョブが見つかりません: {job_id}")
            _store[job_id].update(kwargs)
            _store[job_id]["updatedAt"] = _now()
            return dict(_store[job_id])

    _field_map = {
        "status": "status",
        "steps": "steps",
        "currentStep": "current_step",
        "errorMessage": "error_message",
        "completedAt": "completed_at",
    }

    set_clauses: list[str] = []
    params: list = []

    for key, value in kwargs.items():
        col = _field_map.get(key)
        if col is None:
            continue
        if col == "steps":
            value = json.dumps(value, ensure_ascii=False)
        set_clauses.append(f"`{col}` = %s")
        params.append(value)

    if not set_clauses:
        return await store_get(job_id)

    set_clauses.append("`updated_at` = %s")
    params.append(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f"))
    params.append(job_id)

    query = f"UPDATE jobs SET {', '.join(set_clauses)} WHERE id = %s"
    async with connection._pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, params)

    return await store_get(job_id)


def get_raw_store() -> tuple[dict, asyncio.Lock]:
    return _store, _store_lock
