import requests
import logging


from ipaddress import IPv4Network
from sqlalchemy.orm import Session
from database.models import IPAddress
from utils.env_manager import update_env_var


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def register_server():
    from main_vpn import (
        COUNTRY,
        SERVER_ID,
        NAME,
        MAX_COUNT_USERS,
        MAIN_SERVER,
        SERVER_ENDPOINT,
        REG_TOKEN
    )

    server_data = {
        "server_id": int(SERVER_ID),
        "ip": SERVER_ENDPOINT,
        'name': NAME,
        "country": COUNTRY,
        "max_count_users": int(MAX_COUNT_USERS),
    }

    response = requests.post(
        f'http://{MAIN_SERVER}/auth/register/',
        headers={
            "authorization": f"Bearer {REG_TOKEN}"
        },
        json=server_data,
        timeout=10
    )

    if response.status_code == 200:
        data = response.json()
        token = data.get("token")
        if token:
            update_env_var(
                key='SERVER_JWT_TOKEN',
                value=token
            )
            return True
    return False


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
