from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database.database import get_db
from schemas.server import CreateRequestUser
from utils.config import get_conf
from utils.server import get_server
from database.repository import (
    ServerRepository,
    ConfigRepository,
)
from dependencies import (
    get_server_repo,
    get_config_repo
)


router = APIRouter()


@router.post("/get_available_server/")
async def get_available_server(
    data: CreateRequestUser,
    server_repo: ServerRepository = Depends(get_server_repo),
    config_repo: ConfigRepository = Depends(get_config_repo),
    db: Session = Depends(get_db),
):
    available_server = get_server(db)

    if not available_server:
        raise HTTPException(status_code=503, detail="Все серверы заполнены")

    config_path = await get_conf(
        data.user_id, available_server, db, data.config_name
    )
    if not config_path:
        raise HTTPException(
            status_code=500, detail="Не удалось создать конфигурацию"
        )
    config = config_repo.create(
        user_id=data.user_id,
        server_id=available_server.id,
        config_name=data.config_name,
        months=data.months
    )
    if not config:
        raise HTTPException(
            status_code=500, detail="Не удалось сохранить конфигурацию"
        )
    available_server.count_users += 1
    db.commit()

    return FileResponse(
        config_path,
        filename=f"{data.user_id}_{data.config_name}.conf"
    )
