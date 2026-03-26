"""Admin settings API."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import require_admin_user
from app.schemas.common import ApiInfoResponse

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _mask_key(key: str) -> str:
    if len(key) <= 10:
        return key[:2] + "***" if len(key) > 2 else "***"
    return key[:7] + "***" + key[-3:]


@router.get("/api-info", response_model=ApiInfoResponse)
async def get_api_info(_admin: Annotated[dict, Depends(require_admin_user)]):
    raw = os.environ.get("NOTEVIDEO_API_KEYS", "")
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    masked = [_mask_key(k) for k in keys]
    host = os.environ.get("API_BASE_URL", "http://localhost:8000")
    return ApiInfoResponse(
        base_url=f"{host}/api/v1",
        api_keys=masked,
        has_keys=bool(keys),
    )
