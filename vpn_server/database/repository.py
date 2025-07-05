from sqlalchemy.orm import Session
from typing import Optional
from .models import IPAddress, Clients


class IPRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_free_ip(self) -> Optional[IPAddress]:
        return (
            self.db.query(IPAddress)
            .filter(IPAddress.is_used.is_(False))
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
        return self.db.query(IPAddress).filter(
            IPAddress.address == address,
            IPAddress.client_id == client_id
        ).first()

    def init_ip_pool(self, subnet: str):
        from ipaddress import IPv4Network
        if self.db.query(IPAddress).count() == 0:
            network = IPv4Network(subnet)
            for ip in network.hosts():
                self.db.add(IPAddress(address=str(ip), is_used=False))
            self.db.commit()


class ClientRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id_and_name(
        self, client_id: int, config_name: str
    ) -> Optional[Clients]:
        return self.db.query(Clients).filter(
            Clients.client_id == client_id,
            Clients.config_name == config_name
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
