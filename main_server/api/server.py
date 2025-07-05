import secrets
import os

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from main_server.database.database import get_db
from schemas.server import ServerData, CreateRequestUser
from utils.config import get_conf
from main_server.database.repository import (
    ServerRepository,
    TokenRepository,
    ConfigRepository,
)
from dependencies import (
    get_server_repo,
    get_token_repo,
    get_config_repo
)


router = APIRouter()


@router.post('/register_server/')
async def register_server(
    data: ServerData,
    server_repo: ServerRepository = Depends(get_server_repo),
    token_repo: TokenRepository = Depends(get_token_repo),
):
    check_server = server_repo.get_by_id(data.server_id)
    if not check_server:
        if data.reg_token == os.getenv('REG_TOKEN'):
            server = server_repo.create(
                country=data.country,
                server_id=data.server_id,
                name=data.name,
                ip=data.ip,
                max_count_users=data.max_count_users
            )
            if server:
                token = secrets.token_hex(16)
                obj_token = token_repo.create(
                    server_id=server.id,
                    token=token,
                )
                if obj_token:
                    return {'token': token}
                else:
                    raise HTTPException(
                        status_code=500, detail="Ошибка при добавлении токена"
                    )
            else:
                raise HTTPException(
                    status_code=500, detail="Ошибка при добавлении сервера"
                )
        else:
            raise HTTPException(status_code=401, detail='Unauthorized')
    else:
        token = token_repo.get_by_server(check_server.id)
        if token:
            if token.token == data.token:
                server = server_repo.update(
                    country=data.country,
                    server_id=data.server_id,
                    name=data.name,
                    ip=data.ip,
                    max_count_users=data.max_count_users
                )
                if server:
                    return {'status': 'OK'}
            else:
                raise HTTPException(status_code=401, detail='Unauthorized')
        else:
            raise HTTPException(status_code=401, detail='Unauthorized')


@router.post("/get_available_server/")
async def get_available_server(
    data: CreateRequestUser,
    server_repo: ServerRepository = Depends(get_server_repo),
    config_repo: ConfigRepository = Depends(get_config_repo),
    db: Session = Depends(get_db),
):
    servers = server_repo.get_all_active()
    if not servers:
        raise HTTPException(status_code=503, detail="Нет доступных серверов")

    available_server = None
    for server in servers:
        if server.count_users < server.max_count_users:
            available_server = server
            break

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
