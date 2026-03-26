from typing import Optional

from pydantic import BaseModel


class WikiSyncDirectoryRequest(BaseModel):
    path: Optional[str] = ""
    paths: Optional[list[str]] = None
