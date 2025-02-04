from ipaddress import IPv4Network
import subprocess
import re
import logging
import os
import psutil
import time
import requests

from fastapi.responses import FileResponse
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
from sqlalchemy.orm import Session

from dotenv import load_dotenv
from pathlib import Path



from .database import Base, engine, get_db
from .models import IPAddress
from .crud import *

load_dotenv()


app = FastAPI()
logger = logging.getLogger(__name__)


prev_net_io = psutil.net_io_counters()
prev_time = time.time()


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

@app.on_event("startup")
def initialize():
    # Создание таблиц и инициализация пула IP
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    init_ip_pool(db, SERVER_IP_POOL, SERVER_IP_POOL)
    register_server()



def register_server():
    global TOKEN
    if TOKEN is None:
        response = requests.post(
            f'http://{MAIN_SERVER}/register_server/',
            json={
                'reg_token': REG_TOKEN,
                'country': COUNTRY,
                'server_id': int(SERVER_ID),
                'name': NAME,
                'ip': SERVER_ENDPOINT,
                'max_count_users': int(MAX_COUNT_USERS),
            },
            timeout=10
        )
        if response.status_code != 200:
            logger.error('Не удалось подключиться к главному серверу')
        else:
            data = response.json()
            with open('.env', 'a') as env_file:
                env_file.write(f"TOKEN='{data['token']}'\n")
            TOKEN = data['token']
            logger.info('Подключение к главному серверу выполнено')
    else:
        response = requests.post(
            f'http://{MAIN_SERVER}/register_server/',
            json={
                'reg_token': REG_TOKEN,
                'country': COUNTRY,
                'server_id': int(SERVER_ID),
                'name': NAME,
                'ip': SERVER_ENDPOINT,
                'max_count_users': int(MAX_COUNT_USERS),
                'token': TOKEN
            }
        )
        if response.status_code != 200:
            logger.error('Не удалось подключиться к главному серверу')
        else:
            logger.info('Подключение к главному серверу выполнено')


def init_ip_pool(db: Session, server_id: int, subnet: str):
    """Инициализация пула IP-адресов в БД"""
    if db.query(IPAddress).count() == 0:
        network = IPv4Network(subnet)
        for ip in network.hosts():
            db.add(IPAddress(
                address=str(ip),
                is_used=False
            ))
        db.commit()



def generate_keys() -> tuple[str, str]:
    """Генерирует приватный и публичный ключи WireGuard."""
    private_key = subprocess.run(
        ["wg", "genkey"], 
        capture_output=True, 
        text=True
    ).stdout.strip()
    
    public_key = subprocess.run(
        ["wg", "pubkey"], 
        input=private_key, 
        capture_output=True, 
        text=True
    ).stdout.strip()
    
    return private_key, public_key

def add_client_to_server_config(client_public_key: str, client_ip: str):
    """Добавляет клиента в конфиг сервера."""
    peer_config = f"\n[Peer]\nPublicKey = {client_public_key}\nAllowedIPs = {client_ip}/32\n"
    
    with open("/etc/wireguard/wg0.conf", "a") as f:
        f.write(peer_config)
    
    # Применяем изменения без перезагрузки
    command = "sudo bash -c 'wg syncconf wg0 <(wg-quick strip wg0)'"
    result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )
        
    if result.returncode != 0:
        logger.error(f"Ошибка syncconf: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, result.args)
    
def delete_client_from_server_config(client_public_key: str):
    """Полное удаление пира из конфига и runtime"""
    config_path = Path("/etc/wireguard/wg0.conf")
    
    # Шаг 1: Удаление из runtime-конфигурации
    try:
        subprocess.run(
            ["sudo", "wg", "set", "wg0", "peer", client_public_key, "remove"],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        if "No such peer" not in e.stderr:
            raise RuntimeError(f"Ошибка удаления из runtime: {e.stderr}")

    # Шаг 2: Удаление из конфиг-файла
    config_content = config_path.read_text().splitlines()
    new_content = []
    peer_block = []
    in_target_peer = False

    for line in config_content:
        if line.strip() == "[Peer]":
            if peer_block:
                if not in_target_peer:
                    new_content.extend(peer_block)
                peer_block = []
            in_target_peer = False
            peer_block.append(line)
        elif peer_block:
            peer_block.append(line)
            if line.strip().startswith("PublicKey ="):
                current_key = line.split("=", 1)[1].strip()
                if current_key == client_public_key:
                    in_target_peer = True
        else:
            new_content.append(line)

    # Добавляем последний блок, если не целевой
    if peer_block and not in_target_peer:
        new_content.extend(peer_block)

    # Запись нового конфига
    config_path.write_text("\n".join(new_content) + "\n")

    # Шаг 3: Принудительная синхронизация
    command = "sudo bash -c 'wg syncconf wg0 <(wg-quick strip wg0)'"
    result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )
        
    if result.returncode != 0:
        logger.error(f"Ошибка syncconf: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, result.args)




class ClientRequest(BaseModel):
    user_id: int

@app.post("/generate-config/")
async def generate_config(request: ClientRequest, db: Session = Depends(get_db)):

    # Генерируем ключи
    private_key, public_key = generate_keys()
    
    # Выделяем IP 
    client_ip = get_free_ip_from_pool(db, request.user_id) 
    
    # Создаем конфиг клиента
    config = f"""[Interface]
PrivateKey = {private_key}
Address = {client_ip}/24
DNS = {DNS}

[Peer]
PublicKey = {SERVER_PUBLIC_KEY}
Endpoint = {SERVER_ENDPOINT}:443
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
    
    config_filename = f"{request.user_id}.conf"
    config_path = CONFIGS_DIR / config_filename
        
    with open(config_path, "w") as f:
        f.write(config)

    # Добавляем клиента на сервер
    try:
        add_client_to_server_config(public_key, client_ip)
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка добавления клиента: {e}")
        raise HTTPException(500, "Ошибка настройки сервера")
    
    # Сохраняем в бд
    create_client(db, int(request.user_id), private_key, public_key)    
    return FileResponse(
            path=config_path,
            filename=config_filename,
            media_type="application/octet-stream"
        )



@app.post("/delete-config/")
async def delete_config(
    request: ClientRequest, 
    db: Session = Depends(get_db)
):
    # Получаем клиента из БД
    client = get_client_by_id(db, request.user_id)
    if not client:
        raise HTTPException(404, "Клиент не найден")

    try:
        delete_client_from_server_config(client.public_key)
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка удаления клиента: {e}")
        raise HTTPException(500, "Ошибка настройки сервера")

    # Удаляем клиента из БД и освобождаем IP
    delete = delete_client(db, request.user_id)
    if not delete:
        raise HTTPException(404, 'Ошибка при удалении данных')
    
    # Удаляем файл конфига
    config_path = CONFIGS_DIR / f"{request.user_id}.conf"
    if config_path.exists():
        config_path.unlink()
    
    return {"status": "success"}









@app.get('/status')
async def get_status():
    global prev_net_io, prev_time
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory().percent


    current_net_io = psutil.net_io_counters()
    current_time = time.time()

    # Вычисляем разницу в байтах
    bytes_sent = current_net_io.bytes_sent - prev_net_io.bytes_sent
    bytes_recv = current_net_io.bytes_recv - prev_net_io.bytes_recv
    

    # Вычисляем разницу во времени
    time_diff = current_time - prev_time

    mb_sent = bytes_sent / (1024 * 1024)
    mb_recv = bytes_recv / (1024 * 1024)

    mb_sent_per_sec = mb_sent / time_diff
    mb_recv_per_sec = mb_recv / time_diff

    # Обновляем предыдущие значения
    prev_net_io = current_net_io
    prev_time = current_time

    return {
        "cpu": cpu,
        "memory": memory,
        "sent_traffic": mb_sent_per_sec,
        "recv_traffic": mb_recv_per_sec,
    }