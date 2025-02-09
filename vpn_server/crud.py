from sqlalchemy.orm import Session
from sqlalchemy import and_

from models import IPAddress, Clients

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
    db.refresh(ip)
    return ip


def get_client_by_id(db: Session, client_id: int, config_name: str):
    client = db.query(Clients).filter(Clients.client_id == client_id, Clients.config_name == config_name).first()
    if client:
        return client
    return None

def create_client(db: Session, client_id: int, private_key: str, public_key: str, ip_address: int, config_name:  str):
        client = Clients(
            client_id=client_id,
            privat_key=private_key,
            public_key=public_key,
            ip_address=ip_address,
            config_name=config_name,
        )
        db.add(client)
        db.commit()
        return client


def delete_client(db: Session, client_id: int, config_name: str, ip: int):
    client = db.query(Clients).filter(Clients.client_id == client_id, Clients.config_name == config_name).first()
    ip_address = db.query(IPAddress).filter(IPAddress.address == ip, IPAddress.client_id == client_id).first()
    if client and ip_address:
        db.delete(client)
        ip_address.is_used = False
        ip_address.client_id = 0
        db.commit()
        return 1
    return 0

