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




# def create_item(db: Session, item: schemas.ItemCreate):
#     db_item = models.Item(name=item.name, description=item.description)
#     db.add(db_item)
#     db.commit()
#     db.refresh(db_item)
#     return db_item