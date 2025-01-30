from sqlalchemy.orm import Session
from sqlalchemy import and_

from .models import IPAddress, Clients

def get_free_ip_from_pool(db: Session, server_id: int) -> str:
    """Возвращает свободный IP из пула сервера."""
    # Ищем первый свободный адрес для указанного сервера
    ip = db.query(IPAddress).filter(
        and_(
            IPAddress.server_id == server_id,
            IPAddress.is_used == False
        )
    ).first()

    if not ip:
        raise ValueError("No free IPs in the pool")

    # Помечаем адрес как занятый
    ip.is_used = True
    db.commit()
    
    return ip.address


def get_client_by_id(db: Session, client_id: int):
    client = db.query(Clients).filter(Clients.client_id == client_id)
    if client:
        return client.first()
    return None

def create_client(db: Session, client_id: int, private_key: str, public_key: str):
    client = db.query(Clients).filter(Clients.client_id == client_id)
    if not client:
        client = Clients(client_id, private_key, private_key)
        return client
    return None