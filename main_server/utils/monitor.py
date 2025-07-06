import logging
import requests


from sqlalchemy.orm import Session


from database.database import get_db
from database.repository import ServerRepository


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def monitor_vpn_servers():
    db: Session = next(get_db())
    servers = ServerRepository(db).get_all_active()

    for server in servers:
        try:
            # Отправка запроса с API-ключом в заголовках
            response = requests.get(
                f"http://{server.ip}:8000/status", timeout=10
            )
            data = response.json()
            server.cpu_percent = data["cpu"]
            server.memory_usage = data["memory"]
            server.sent_traffic = data["sent_traffic"]
            server.recv_traffic = data["recv_traffic"]

            db.commit()
        except Exception as e:
            logger.error(f"Ошибка опроса сервера {server.name}: {str(e)}")
            server.status = False
            db.commit()
