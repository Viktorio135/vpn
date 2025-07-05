from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, BigInteger

from vpn_server.database.database import Base


class IPAddress(Base):
    __tablename__ = "ip_addresses"

    id = Column(Integer, primary_key=True)
    address = Column(String(15), unique=True)  # Пример: "10.0.0.2"
    is_used = Column(Boolean, default=False)   # Занят ли адрес
    client_id = Column(BigInteger, default=0)


class Clients(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    client_id = Column(BigInteger)
    privat_key = Column(String(500))
    public_key = Column(String(500))
    config_name = Column(String(100), unique=True)
    ip_address = Column(Integer, ForeignKey('ip_addresses.id'))
