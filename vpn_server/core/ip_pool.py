import requests
import logging


from ipaddress import IPv4Network
from sqlalchemy.orm import Session
from database.models import IPAddress
from main_vpn import (
    REG_TOKEN,
    COUNTRY,
    SERVER_ID,
    NAME,
    MAX_COUNT_USERS,
    MAIN_SERVER,
    SERVER_ENDPOINT
)


logger = logging.getLogger(__name__)


def register_server():
    global TOKEN
    if TOKEN is None:
        response = requests.post(
            f'http://{MAIN_SERVER}/server/register_server/',
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
            f'http://{MAIN_SERVER}/server/register_server/',
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
