from sqlalchemy.orm import Session
from sqlalchemy import and_

from .models import IPAddress, Clients

def get_free_ip_from_pool(db: Session, user_id: int) -> str:
    """Возвращает свободный IP из пула сервера."""
    # Ищем первый свободный адрес для указанного сервера
    ip = db.query(IPAddress).filter(
            IPAddress.is_used == False
    ).first()

    if not ip:
        raise ValueError("No free IPs in the pool")

    # Помечаем адрес как занятый
    ip.is_used = True
    ip.client_id = user_id
    db.commit()

    return ip.address


def get_client_by_id(db: Session, client_id: int):
    client = db.query(Clients).filter(Clients.client_id == client_id)
    if client:
        return client.first()
    return None

def create_client(db: Session, client_id: int, private_key: str, public_key: str):
    client = db.query(Clients).filter(Clients.client_id == client_id).first()
    if not client:
        client = Clients(
            client_id=client_id,
            privat_key=private_key,
            public_key=public_key
        )
        db.add(client)
        db.commit()
        return client
    return None


def delete_client(db: Session, client_id: int):
    client = db.query(Clients).filter(Clients.client_id == client_id).first()
    ip_adress = db.query(IPAddress).filter(IPAddress.client_id == client_id).first()
    if client and ip_adress:
        db.delete(client)
        ip_adress.is_used = False
        ip_adress.client_id = 0
        db.commit()
        return 1
    return 0