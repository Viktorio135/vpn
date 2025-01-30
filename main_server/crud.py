from sqlalchemy.orm import Session
import models


def get_server(db: Session, item_ip: str):
    return db.query(models.Servers).filter(models.Servers.ip == item_ip).first()

def get_all_servers(db: Session):
    return db.query(models.Servers).all()

def add_user(db: Session, server_id: int):
    try:
        server = db.query(models.Servers).filter(models.Servers.id==server_id).first()
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
    db_client = models.Client(
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
    return db.query(models.Client).filter(models.Client.user_id == user_id).first()


