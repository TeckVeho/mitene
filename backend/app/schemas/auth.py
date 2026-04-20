from pydantic import BaseModel


class AuthStatus(BaseModel):
    status: str


class LoginResponse(BaseModel):
    message: str


class UploadSessionRequest(BaseModel):
    session_json: str

