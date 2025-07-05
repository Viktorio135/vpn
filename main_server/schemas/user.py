from pydantic import BaseModel


class UserCreate(BaseModel):
    user_id: int


class DeleteRequestUser(BaseModel):
    user_id: int
    config_name: str | None = None
    token: str
