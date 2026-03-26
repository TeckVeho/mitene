from typing import Optional

from pydantic import BaseModel


class UserLoginRequest(BaseModel):
    email: str
    displayName: str


class UserResponse(BaseModel):
    id: str
    email: str
    displayName: str
    createdAt: str
    isAdmin: bool = False


class WatchRequest(BaseModel):
    completed: bool = True


class WatchHistoryItem(BaseModel):
    id: str
    userId: str
    videoId: str
    videoTitle: Optional[str] = None
    videoStatus: Optional[str] = None
    categoryName: Optional[str] = None
    categorySlug: Optional[str] = None
    completed: bool
    watchedAt: str
