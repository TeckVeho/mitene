"""Category listing."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter

import database
from app.schemas.common import CategoryResponse

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryResponse])
async def get_categories(locale: Optional[str] = None):
    language = locale if locale in ("ja", "vi") else "ja"
    cats = await database.get_categories(language=language)
    return [
        CategoryResponse(
            id=c["id"],
            name=c["name"],
            slug=c["slug"],
            description=c.get("description"),
            sortOrder=c.get("sort_order", c.get("sortOrder", 0)),
            videoCount=c.get("videoCount", c.get("video_count", 0)),
        )
        for c in cats
    ]
