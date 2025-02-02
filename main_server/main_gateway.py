import logging
import httpx
import requests
import secrets
import os

from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler


from .crud import *
from .database import get_db, engine
from .models import Servers, Base

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

def monitor_vpn_servers():
    db: Session = next(get_db())
    servers = get_all_servers(db)
    
    for server in servers:
        try:
            # Отправка запроса с API-ключом в заголовках
            response = requests.get(f"http://{server.ip}:8000/status", timeout=10)
            data = response.json()
            server.cpu_percent = data["cpu"]
            server.memory_usage = data["memory"]
            server.sent_traffic = data["sent_traffic"]
            server.recv_traffic = data["recv_traffic"]
            
            db.commit()
            print('eee')
        except Exception as e:
            logger.error(f"Ошибка опроса сервера {server.name}: {str(e)}")



@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    scheduler = BackgroundScheduler()
    scheduler.add_job(monitor_vpn_servers, 'interval', minutes=5)
    scheduler.start()


# Директория для хранения конфигураций
CONFIGS_DIR = Path("./confs")
CONFIGS_DIR.mkdir(exist_ok=True)

class RequestUser(BaseModel):
    user_id: int


async def get_conf(user_id: int, server: Servers, db: Session = Depends(get_db)) -> str:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{server.ip}:8000/generate-config/",
                json={"user_id": user_id}
            )

            # Сохраняем конфигурацию на диск
            config_path = CONFIGS_DIR / f"{user_id}.conf"
            with open(config_path, "wb") as file:
                file.write(response.content)

            # Добавляем пользователя в базу данных
            if not add_user(db=db, server_id=server.id):
                logger.error(f"Не удалось добавить пользователя {user_id} на сервер {server.id}")
                raise HTTPException(status_code=500, detail="Ошибка при добавлении пользователя")

            return str(config_path)

    except httpx.HTTPStatusError as e:
        logger.error(f"Ошибка при запросе к серверу {server.id}: {e}")#поменять на server.id
        raise HTTPException(status_code=502, detail="Ошибка при запросе к VPN-серверу")
    except Exception as e:
        logger.error(f"Неизвестная ошибка: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")



class ServerData(BaseModel):
    reg_token: str = 'none'
    country: str
    server_id: int
    name: str
    ip: str
    max_count_users: int
    token: str = 'none'




@app.post('/register_server/')
async def register_server(data: ServerData, db: Session = Depends(get_db)):
    check_server = db.query(Servers).filter(Servers.server_id == data.server_id).first()
    if not check_server:
        if data.reg_token == os.getenv('REG_TOKEN'):
            server = create_server(
                db, 
                country=data.county,
                server_id=data.server_id,
                name=data.name,
                ip=data.ip,
                max_count_users=data.max_count_users
            )
            if server:
                token = secrets.token_hex(16)
                obj_token = create_token(
                    db, 
                    server_id=server.id,
                    token=token,
                )
                if obj_token:
                    return {'token': token}
                else:
                    raise HTTPException(status_code=500, detail="Ошибка при добавлении токена")
            else:
                raise HTTPException(status_code=500, detail="Ошибка при добавлении сервера")
        else:
            raise HTTPException(status_code=401, detail='Unauthorized')
    else:
        token = db.query(Tokens).filter(Tokens.server == check_server.id).first()
        if token:
            if token.token == data.token:
                server = update_server(
                    db, 
                    country=data.county,
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

                
        

        



@app.post("/get_available_server/")
async def get_available_server(data: RequestUser, db: Session = Depends(get_db)):

    servers = get_all_servers(db=db)
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
    config_path = await get_conf(data.user_id, available_server, db)
    if not config_path:
        raise HTTPException(status_code=500, detail="Не удалось создать конфигурацию")
    available_server.count_users += 1
    db.commit()
    

    return FileResponse(config_path, filename=f"{data.user_id}.conf")


@app.post('/statuses/')
async def get_statuses(db: Session = Depends(get_db)):
    servers = get_all_servers(db=db)
    response = {}
    for server in servers:
        response[server.ip] = {
            'cpu': server.cpu_percent,
            'ram': server.memory_usage,
            'sent_traffic': server.sent_traffic,
            'recv_traffic': server.recv_traffic
        }
    return response
