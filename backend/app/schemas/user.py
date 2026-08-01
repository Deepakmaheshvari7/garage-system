from pydantic import BaseModel, ConfigDict

from app.models.user import RoleEnum


class UserCreate(BaseModel):
    username: str
    password: str
    role: RoleEnum


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    role: RoleEnum


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: RoleEnum
    user_id: int
    username: str
