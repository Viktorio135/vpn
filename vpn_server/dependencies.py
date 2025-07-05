from database.repository import (
    IPRepository,
    ClientRepository,
)


def get_ip_repository(db):
    """
    Dependency to get IPRepository instance.
    """
    return IPRepository(db)


def get_client_repository(db):
    """
    Dependency to get ClientRepository instance.
    """
    return ClientRepository(db)
