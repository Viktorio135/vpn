import datetime

from pydantic import BaseModel


class ConfigInfoResponse(BaseModel):
    id: int
    config_name: str
    created_at: datetime.datetime
    expires_at: datetime.datetime


class RenewRequest(BaseModel):
    months: int
