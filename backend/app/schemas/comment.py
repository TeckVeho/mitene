from typing import List, Optional

from pydantic import BaseModel, Field


class CommentResponse(BaseModel):
    id: str
    videoId: str
    userId: str
    displayName: str
    text: str
    likeCount: int
    likedByMe: bool
    createdAt: str
    parentId: Optional[str] = None
    replies: List["CommentResponse"] = Field(default_factory=list)


class CreateCommentBody(BaseModel):
    text: str
    parentId: Optional[str] = None


CommentResponse.model_rebuild()
