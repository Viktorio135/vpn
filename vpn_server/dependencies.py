from fastapi import Depends
from database.database import get_db

from database.repository import (
    IPRepository,
    ClientRepository,
)


def get_ip_repository(db=Depends(get_db)):
    """
    Dependency to get IPRepository instance.
    """
    return IPRepository(db)


def get_client_repository(db=Depends(get_db)):
    """
    Dependency to get ClientRepository instance.
    """
    return ClientRepository(db)
