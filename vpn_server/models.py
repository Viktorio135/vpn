from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, BigInteger

from .database import Base


class IPAddress(Base):
    __tablename__ = "ip_addresses"

    id = Column(Integer, primary_key=True)
    address = Column(String(15), unique=True)  # Пример: "10.0.0.2"
    is_used = Column(Boolean, default=False)   # Занят ли адрес

class Clients(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    client_id = Column(BigInteger)
    privat_key = Column(String(500))
    public_key = Column(String(500))