import httpx
import logging
import os

from fastapi import Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import Servers
from database.repository import ServerRepository, TokenRepository, ConfigRepository, BaseRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_conf(
        user_id: int, server: Servers,
        db: Session = Depends(get_db),
        config_name: str | None = None
) -> str:
    try:
        token_repo = TokenRepository(db)
        server_repo = ServerRepository(db)

        async with httpx.AsyncClient() as client:
            token = token_repo.get_by_server(server.id)
            if not token:
                logger.error(f"Токен для сервера {server.id} не найден")
                raise HTTPException(status_code=400, detail="Токен не найден")

            response = await client.post(
                f"http://{server.ip}:8000/client/generate-config/",
                json={
                    "user_id": user_id,
                    "config_name": config_name,
                    "token": token.token,
                }
            )
            if response.status_code == 401:
                raise HTTPException(status_code=401, detail='Unauthorized')
            logger.info(f"{user_id} запрошен конфиг на сервере {server.id} {response.content}")
            # Сохраняем конфигурацию на диск
            from main_gateway import CONFIGS_DIR

            config_path = CONFIGS_DIR / f"{user_id}_{config_name}.conf"
            with open(config_path, "wb") as file:
                file.write(response.content)

            # Добавляем пользователя на сервер через репозиторий
            if not server_repo.add_user(server_id=server.id):
                logger.error(
                    (
                        f"Не удалось добавить пользователя {user_id} "
                        f"на сервер {server.id}"
                    )
                )
                raise HTTPException(
                    status_code=500,
                    detail="Ошибка при добавлении пользователя"
                )

            return str(config_path)

    except httpx.HTTPStatusError as e:
        logger.error(f"Ошибка при запросе к серверу {server.id}: {e}")
        raise HTTPException(
            status_code=502,
            detail="Ошибка при запросе к VPN-серверу"
        )
    except Exception as e:
        logger.error(f"Неизвестная ошибка: {e}")
        raise HTTPException(
            status_code=500, detail="Внутренняя ошибка сервера"
        )


async def delete_config(
        user_id: int, config_name: str,
        db: Session
):

    config_repo = ConfigRepository(db)
    server_repo = ServerRepository(db)
    token_repo = TokenRepository(db)

    config = config_repo.get_by_user_and_name(user_id, config_name)
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
            f"http://{server.ip}:8000/client/delete-config/",
            json={
                "user_id": user_id,
                "config_name": config_name,
                "token": token.token,
            }
        )
    if response.status_code != 200:
        raise HTTPException(
            status_code=500,
            detail='Невозможно обратиться к впн серверу'
        )

    from main_gateway import CONFIGS_DIR

    path = CONFIGS_DIR / f"{user_id}_{config_name}.conf"

    if os.path.exists(path):
        os.remove(path)
    config_repo.delete(config.id)

    return {"status": "deleted"}


async def reinstall_config(
        config_id: int,
        db: Session
):
    config_repo = ConfigRepository(db)
    server_repo = ServerRepository(db)
    token_repo = TokenRepository(db)

    config = config_repo.get_by_id(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    server = server_repo.get_by_id(config.server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    token = token_repo.get_by_server(server.id)
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")

    await delete_config(
        user_id=config.user_id,
        config_name=config.config_name,
        db=db
    )
    await get_conf(
        user_id=config.user_id,
        server=server,
        db=db,
        config_name=config.config_name
    )
    new_config = BaseRepository.create(
        config_repo,
        user_id=config.user_id,
        server_id=config.server_id,
        config_name=config.config_name,
        created_at=config.created_at,
        expires_at=config.expires_at
    )

    return {"status": "reinstalled", "config_id": new_config.id}
