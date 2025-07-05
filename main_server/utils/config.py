import httpx
import logging


from fastapi import Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session


from main_server.database.database import get_db
from main_server.database.models import Servers, Tokens
from main_gateway import CONFIGS_DIR
from main_server.database.repository import add_user


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_conf(
        user_id: int, server: Servers,
        db: Session = Depends(get_db),
        config_name: str | None = None
) -> str:
    try:
        async with httpx.AsyncClient() as client:
            token = db.query(Tokens).filter(Tokens.server == server.id).first()

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

            # Сохраняем конфигурацию на диск
            config_path = CONFIGS_DIR / f"{user_id}_{config_name}.conf"
            with open(config_path, "wb") as file:
                file.write(response.content)

            # Добавляем пользователя в базу данных
            if not add_user(db=db, server_id=server.id):
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
