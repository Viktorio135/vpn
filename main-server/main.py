import logging
import httpx

from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel


import crud
from database import get_db, engine
from models import Servers, Base

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


# Директория для хранения конфигураций
CONFIGS_DIR = Path("./confs")
CONFIGS_DIR.mkdir(exist_ok=True)

class RequestUser(BaseModel):
    user_request: int


async def get_conf(user_id: int, server: Servers, db: Session = Depends(get_db)) -> str:
    """
    Запрашивает конфигурацию у VPN-сервера и сохраняет её на диск.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{server.ip}/get_conf/",#поменять на server.id
                json={"filename": str(user_id)}
            )

            # Сохраняем конфигурацию на диск
            config_path = CONFIGS_DIR / f"{user_id}.conf"
            with open(config_path, "wb") as file:
                file.write(response.content)

            # Добавляем пользователя в базу данных
            if not crud.add_user(db=db, server_id=server.id):
                logger.error(f"Не удалось добавить пользователя {user_id} на сервер {server.id}")
                raise HTTPException(status_code=500, detail="Ошибка при добавлении пользователя")

            return str(config_path)

    except httpx.HTTPStatusError as e:
        logger.error(f"Ошибка при запросе к серверу {server.id}: {e}")#поменять на server.id
        raise HTTPException(status_code=502, detail="Ошибка при запросе к VPN-серверу")
    except Exception as e:
        logger.error(f"Неизвестная ошибка: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@app.post("/get_available_server/")
async def get_available_server(data: RequestUser, db: Session = Depends(get_db)):

    servers = crud.get_all_servers(db=db)
    if not servers:
        raise HTTPException(status_code=503, detail="Нет доступных серверов")

    # Ищем сервер с минимальной нагрузкой
    available_server = None
    for server in servers:
        if server.count_users < server.max_count_users:
            available_server = server
            break

    if not available_server:
        raise HTTPException(status_code=503, detail="Все серверы заполнены")

    # Создаем конфигурацию для пользователя
    config_path = await get_conf(data.user_request, available_server, db)
    if not config_path:
        raise HTTPException(status_code=500, detail="Не удалось создать конфигурацию")

    return FileResponse(config_path, filename=f"{data.user_request}.conf")