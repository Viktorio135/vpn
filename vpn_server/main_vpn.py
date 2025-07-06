import os
import psutil
import time

from fastapi import FastAPI
from dotenv import load_dotenv
from pathlib import Path
from contextlib import asynccontextmanager


from database.database import Base, engine, get_db
from core.ip_pool import init_ip_pool, register_server
from api.client import router as client_router
from api.status import router as status_router


load_dotenv()



CONFIGS_DIR = Path("./configs")
CONFIGS_DIR.mkdir(exist_ok=True)

# Конфигурация сервера
SERVER_PUBLIC_KEY = os.getenv('SERVER_PUBLIC_KEY')
SERVER_ENDPOINT = os.getenv('SERVER_ENDPOINT')
SERVER_IP_POOL = "10.0.0.0/24"
DNS = "1.1.1.1"
REG_TOKEN = os.getenv('REG_TOKEN')
COUNTRY = os.getenv('COUNTRY')
SERVER_ID = os.getenv('SERVER_ID')
NAME = os.getenv('NAME')
MAX_COUNT_USERS = os.getenv('MAX_COUNT_USERS')
TOKEN = os.getenv('TOKEN')
MAIN_SERVER = os.getenv('MAIN_SERVER')


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    init_ip_pool(db, SERVER_IP_POOL, SERVER_IP_POOL)
    register_server()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(client_router, prefix="/client", tags=["client"])
app.include_router(status_router, prefix="/status", tags=["status"])
