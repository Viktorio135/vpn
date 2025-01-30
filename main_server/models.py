import datetime
from sqlalchemy import Column, DateTime, Integer, String, ForeignKey
from database import Base

class Servers(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    country = Column(String(200), index=True)
    server_id = Column(Integer, index=True)
    name = Column(String(200), index=True)
    ip = Column(String(200), index=True)
    max_count_users = Column(Integer, index=True)
    count_users = Column(Integer, default=0, index=True)
   

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), unique=True, index=True)
    private_key = Column(String(255))  # Шифровать на проде!
    public_key = Column(String(255))
    server_id = Column(Integer, ForeignKey("servers.id"))
    ip_address = Column(String(15))
    created_at = Column(DateTime, default=datetime.utcnow)