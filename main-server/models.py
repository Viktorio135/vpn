from sqlalchemy import Column, Integer, String
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
   