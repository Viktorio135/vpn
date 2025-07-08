import logging


from sqlalchemy.orm import Session
from typing import Optional
from .models import IPAddress, Clients


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseRepository:
    model = None

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, obj_id: int):
        return self.db.query(self.model).filter(self.model.id == obj_id).first()

    def get_all(self):
        return self.db.query(self.model).all()

    def create(self, **kwargs):
        obj = self.model(**kwargs)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        logger.info(f"[{self.__class__.__name__}] Created: {obj.id}")
        return obj

    def update(self, obj_id: int, **kwargs):
        obj = self.get_by_id(obj_id)
        if not obj:
            logger.warning(f"[{self.__class__.__name__}] Not found for update: {obj_id}")
            return None
        for key, value in kwargs.items():
            setattr(obj, key, value)
        self.db.commit()
        logger.info(f"[{self.__class__.__name__}] Updated: {obj.id}")
        return obj

    def delete(self, obj_id: int):
        obj = self.get_by_id(obj_id)
        if not obj:
            logger.warning(f"[{self.__class__.__name__}] Not found for delete: {obj_id}")
            return False
        self.db.delete(obj)
        self.db.commit()
        logger.info(f"[{self.__class__.__name__}] Deleted: {obj.id}")
        return True


class IPRepository(BaseRepository):
    model = IPAddress

    def __init__(self, db: Session):
        self.db = db

    def get_free_ip(self) -> Optional[IPAddress]:
        return (
            self.db.query(self.model)
            .filter(self.model.is_used.is_(False))
            .first()
        )

    def mark_ip_used(self, ip: IPAddress, user_id: int):
        ip.is_used = True
        ip.client_id = user_id
        self.db.commit()
        self.db.refresh(ip)
        return ip

    def free_ip(self, ip: IPAddress):
        ip.is_used = False
        ip.client_id = 0
        self.db.commit()
        self.db.refresh(ip)
        return ip

    def get_by_address_and_client(
        self, address: str, client_id: int
    ) -> Optional[IPAddress]:
        return self.db.query(self.model).filter(
            self.model.address == address,
            self.model.client_id == client_id
        ).first()

    def init_ip_pool(self, subnet: str):
        from ipaddress import IPv4Network
        if self.db.query(self.model).count() == 0:
            network = IPv4Network(subnet)
            for ip in network.hosts():
                self.db.add(self.model(address=str(ip), is_used=False))
            self.db.commit()


class ClientRepository(BaseRepository):
    model = Clients

    def __init__(self, db: Session):
        self.db = db

    def get_by_id_and_name(
        self, client_id: int, config_name: str
    ) -> Optional[Clients]:
        return self.db.query(self.model).filter(
            self.model.client_id == client_id,
            self.model.config_name == config_name
        ).first()

    def create(
        self,
        client_id: int,
        private_key: str,
        public_key: str,
        ip_address: int,
        config_name: str
    ) -> Clients:
        client = Clients(
            client_id=client_id,
            privat_key=private_key,
            public_key=public_key,
            ip_address=ip_address,
            config_name=config_name,
        )
        self.db.add(client)
        self.db.commit()
        self.db.refresh(client)
        return client

    def delete(self, client: Clients):
        self.db.delete(client)
        self.db.commit()
