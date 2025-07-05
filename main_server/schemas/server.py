from pydantic import BaseModel


class ServerData(BaseModel):
    reg_token: str = 'none'
    country: str
    server_id: int
    name: str
    ip: str
    max_count_users: int
    token: str = 'none'


class CreateRequestUser(BaseModel):
    user_id: int
    config_name: str | None = None
    months: int
