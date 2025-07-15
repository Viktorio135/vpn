from pydantic import BaseModel


class CreateClientRequest(BaseModel):
    user_id: int
    config_name: str


class DeleteClientRequest(BaseModel):
    user_id: int
    config_name: str
