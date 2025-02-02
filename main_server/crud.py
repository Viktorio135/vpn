from sqlalchemy.orm import Session
from .models import Servers, Client, Tokens
from sqlalchemy.exc import IntegrityError
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_server(db: Session, item_ip: str):
    return db.query(Servers).filter(Servers.ip == item_ip).first()

def get_all_servers(db: Session):
    return db.query(Servers).filter(Servers.status).all()

def add_user(db: Session, server_id: int):
    try:
        server = db.query(Servers).filter(Servers.id==server_id).first()
        server.count_users = server.count_users + 1
        db.commit()
        return 1
    except:
        return 0

def create_client(
    db: Session, 
    user_id: str, 
    private_key: str, 
    public_key: str, 
    server_id: int, 
    ip: str
):
    db_client = Client(
        user_id=user_id,
        private_key=private_key,
        public_key=public_key,
        server_id=server_id,
        ip_address=ip
    )
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client

def get_client_by_user_id(db: Session, user_id: str):
    return db.query(Client).filter(Client.user_id == user_id).first()



def create_server(
    db: Session,
    country: str,
    server_id: int,
    name: str,
    ip: str,
    max_count_users: int,
):
    server = Servers(
        country=country,
        server_id=server_id,
        name=name,
        ip=ip,
        max_count_users=max_count_users
    )

    db.add(server)
    db.commit()
    return server


def update_server(
    db: Session,
    country: str,
    server_id: int,
    name: str,
    ip: str,
    max_count_users: int,
):
    server = db.query(Servers).filter(Servers.server_id == server_id).first()
    if server:
        server.country = country
        server.name = name
        server.ip = ip
        server.max_count_users = max_count_users
        server.status = True
        db.commit()
        return server
    else:
        return 0





def create_token(db: Session, server_id: int, token: str):
    try:
        # Получаем сервер по server_id
        server = db.query(Servers).get(server_id)
        if not server:
            logger.error(f"Server not found: {server_id}")
            return None

        # Создаем объект токена
        obj_token = Tokens(
            server=server.id,
            token=token
        )

        # Добавляем и сохраняем в базе данных
        db.add(obj_token)
        db.commit()
        db.refresh(obj_token)

        logger.info(f"Token created for server {server_id}: {obj_token.id}")
        return obj_token

    except IntegrityError as e:
        # Обработка ошибок целостности (например, дубликат токена)
        db.rollback()
        logger.error(f"IntegrityError: {e}")
        return None

    except Exception as e:
        # Обработка всех остальных исключений
        db.rollback()
        logger.error(f"Error creating token: {e}")
        return None