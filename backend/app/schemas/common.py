from typing import Optional

from pydantic import BaseModel


class ApiInfoResponse(BaseModel):
    base_url: str
    api_keys: list[str]
    has_keys: bool


class CategoryResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    sortOrder: int = 0
    videoCount: int = 0


class ArticleResponse(BaseModel):
    id: str
    title: str
    gitPath: str
    gitHash: Optional[str] = None
    categoryId: Optional[str] = None
    categoryName: Optional[str] = None
    latestVideoId: Optional[str] = None
    latestVideoStatus: Optional[str] = None
    createdAt: str
    updatedAt: str
