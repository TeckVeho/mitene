from typing import Optional

from pydantic import BaseModel


class VideoResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    thumbnailUrl: Optional[str] = None
    durationSec: Optional[int] = None
    style: Optional[str] = None
    status: str
    publishedAt: Optional[str] = None
    createdAt: str
    updatedAt: str
    jobId: Optional[str] = None
    articleId: Optional[str] = None
    categoryId: Optional[str] = None
    categoryName: Optional[str] = None
    categorySlug: Optional[str] = None
    watched: Optional[bool] = None
    watchLater: Optional[bool] = None
    liked: Optional[bool] = None
    wikiUrl: Optional[str] = None
    viewerCount: int = 0
    viewCount: int = 0


class AdminVideoPatchRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    thumbnailUrl: Optional[str] = None
    durationSec: Optional[int] = None
    publishedAt: Optional[str] = None
    style: Optional[str] = None
    language: Optional[str] = None
