from ipaddress import IPv4Network
import subprocess
import re
import logging
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
from sqlalchemy.orm import Session


from .database import Base, engine, get_db
from .models import IPAddress
from .crud import get_free_ip_from_pool, create_client



app = FastAPI()
logger = logging.getLogger(__name__)

# Конфигурация сервера
SERVER_PUBLIC_KEY = os.getenv('SERVER_PUBLIC_KEY')
SERVER_ENDPOINT = os.getenv('SERVER_ENDPOINT')
SERVER_IP_POOL = "10.0.0.0/24"
DNS = "1.1.1.1"

@app.on_event("startup")
def initialize():
    # Создание таблиц и инициализация пула IP
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    init_ip_pool(db, SERVER_IP_POOL, SERVER_IP_POOL)

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


# Хранилище клиентов {имя: приватный_ключ}

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
    subprocess.run(["wg", "syncconf", "wg0", "/etc/wireguard/wg0.conf"], check=True)

class ClientRequest(BaseModel):
    user_id: int

@app.post("/generate-config/")
async def generate_config(request: ClientRequest):

    # Генерируем ключи
    private_key, public_key = generate_keys()
    
    # Выделяем IP 
    client_ip = get_free_ip_from_pool() 
    
    # Создаем конфиг клиента
    config = f"""[Interface]
PrivateKey = {private_key}
Address = {client_ip}
DNS = {DNS}

[Peer]
PublicKey = {SERVER_PUBLIC_KEY}
Endpoint = {SERVER_ENDPOINT}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
    
    # Добавляем клиента на сервер
    try:
        add_client_to_server_config(public_key, client_ip)
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка добавления клиента: {e}")
        raise HTTPException(500, "Ошибка настройки сервера")
    
    # Сохраняем в бд
    create_client(int(request.user_id), private_key, public_key)    
    return {"config": config}

