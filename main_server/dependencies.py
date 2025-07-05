from fastapi import Depends


from database.database import get_db
from database.repository import (
    UserRepository,
    ConfigRepository,
    ServerRepository,
    TokenRepository
)


def get_user_repo(db=Depends(get_db)):
    return UserRepository(db)


def get_config_repo(db=Depends(get_db)):
    return ConfigRepository(db)


def get_server_repo(db=Depends(get_db)):
    return ServerRepository(db)


def get_token_repo(db=Depends(get_db)):
    return TokenRepository(db)
