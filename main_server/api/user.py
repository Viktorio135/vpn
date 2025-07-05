import httpx
import os

from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException

from schemas.user import UserCreate, DeleteRequestUser
from schemas.config import ConfigInfoResponse
from main_server.database.repository import (
    UserRepository,
    ConfigRepository,
    ServerRepository,
    TokenRepository,
)
from main_gateway import CONFIGS_DIR
from dependencies import (
    get_user_repo,
    get_config_repo,
    get_server_repo,
    get_token_repo,
)


router = APIRouter()


@router.post("/create_user/")
async def create_user_view(
    user_data: UserCreate,
    user_repo: UserRepository = Depends(get_user_repo)
):
    try:
        user = user_repo.create(user_id=user_data.user_id)
        if user:
            return {"status": "created"}
        raise HTTPException(status_code=400, detail="User already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/delete_user/')
async def delete_user(
    data: DeleteRequestUser,
    config_repo: ConfigRepository = Depends(get_config_repo),
    server_repo: ServerRepository = Depends(get_server_repo),
    token_repo: TokenRepository = Depends(get_token_repo),
):
    config = config_repo.get_by_user_and_name(data.user_id, data.config_name)
    if not config:
        raise HTTPException(status_code=400, detail='Конфига не существует')
    server = server_repo.get_by_id(config.server_id)
    if not server:
        raise HTTPException(status_code=400, detail='Сервера не существует')

    token = token_repo.get_by_server(config.server_id)
    if not token:
        raise HTTPException(status_code=400, detail='Токен не найден')

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://{server.ip}:8000/delete-config/",
            json={
                "user_id": data.user_id,
                "config_name": data.config_name,
                "token": token.token,
            }
        )
    if response.status_code != 200:
        raise HTTPException(
            status_code=500,
            detail='Невозможно обратиться к впн серверу'
        )

    path = CONFIGS_DIR / f"{data.user_id}_{data.config_name}.conf"

    if os.path.exists(path):
        os.remove(path)
    config_repo.delete_by_id(config.id)

    return {'delete': 'OK'}


@router.get("/{user_id}/")
async def get_user(
    user_id: int,
    user_repo: UserRepository = Depends(get_user_repo)
):
    user = user_repo.get_by_id(user_id)
    if user:
        return user
    raise HTTPException(status_code=404, detail="User not created")


@router.get("/{user_id}/configs/")
async def get_user_configs(
    user_id: int,
    config_repo: ConfigRepository = Depends(get_config_repo)
):
    configs = config_repo.get_by_user(user_id)
    return [ConfigInfoResponse(
        id=c.id,
        config_name=c.config_name,
        created_at=c.created_at,
        expires_at=c.expires_at
    ) for c in configs]
