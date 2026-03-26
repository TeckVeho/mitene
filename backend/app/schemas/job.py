from typing import Optional

from pydantic import BaseModel


class JobStepInfo(BaseModel):
    id: str
    label: str
    status: str
    message: Optional[str] = None


class Job(BaseModel):
    id: str
    jobType: str = "video"
    csvFileNames: str
    notebookTitle: str
    instructions: str
    style: Optional[str] = None
    format: Optional[str] = None
    language: str
    timeout: int
    status: str
    steps: list[JobStepInfo]
    currentStep: Optional[str] = None
    errorMessage: Optional[str] = None
    createdAt: str
    updatedAt: str
    completedAt: Optional[str] = None
    callbackUrl: Optional[str] = None


class JobStats(BaseModel):
    total: int
    processing: int
    completed: int
    error: int
