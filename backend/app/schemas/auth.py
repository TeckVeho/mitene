from pydantic import BaseModel


class AuthStatus(BaseModel):
    status: str


class LoginResponse(BaseModel):
    message: str
