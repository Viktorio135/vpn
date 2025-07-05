import datetime
from sqlalchemy import (Column, DateTime, Integer, String,
                        ForeignKey, Boolean, Float, BigInteger)
from main_server.database.database import Base


class Servers(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    country = Column(String(200), index=True)
    server_id = Column(Integer, index=True)
    name = Column(String(200), index=True)
    ip = Column(String(200), index=True)
    max_count_users = Column(Integer, index=True)
    count_users = Column(Integer, default=0, index=True)
    status = Column(Boolean, default=True)
    cpu_percent = Column(Float, default=0)
    memory_usage = Column(Float, default=0)
    sent_traffic = Column(Float, default=0)
    recv_traffic = Column(Float, default=0)


class User(Base):
    __tablename__ = "users"
    # id = Column(Integer, primary_key=True)
    client_id = Column(BigInteger, primary_key=True)


class WGConfig(Base):
    __tablename__ = "wireguard_configs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.client_id'), index=True)
    server_id = Column(Integer, ForeignKey('servers.id'))
    config_name = Column(String(100))  # Пользовательское имя конфига
    created_at = Column(DateTime, default=datetime.datetime.now)
    expires_at = Column(DateTime)      # Срок действия конфига


class Tokens(Base):
    __tablename__ = "tokens"
    id = Column(Integer, primary_key=True, index=True)
    server = Column(Integer, ForeignKey('servers.id'))
    token = Column(String(40))
