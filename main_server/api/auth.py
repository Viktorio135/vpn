import os
import logging


from fastapi import APIRouter, Depends, Header
from fastapi.exceptions import HTTPException


from schemas.server import ServerData
from utils.security import create_jwt_token
from database.repository import (ServerRepository)
from dependencies import get_server_repo


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post('/register/')
async def register_server(
    server_data: ServerData,
    authorization: str = Header(None),
    server_repo: ServerRepository = Depends(get_server_repo)
):
    if not authorization or not authorization.startswith("Bearer "):
        logger.info("Main_server: Authorization header missing")
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing"
        )

    reg_token = authorization.split(" ")[1]

    if reg_token != os.getenv("REG_TOKEN"):
        logger.info("Main_server: Invalid token")
        raise HTTPException(status_code=401, detail="Invalid token")

    server_dict = server_data.model_dump(
        exclude={'token', 'reg_token'}
    )

    server = server_repo.get_by_id(int(server_dict['server_id']))

    if not server:
        server = server_repo.create(**server_dict)

    token = create_jwt_token(data=server_dict)
    logger.info("Main_server: token created")

    return {"token": token}
