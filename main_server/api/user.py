from fastapi import APIRouter, Depends
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session

from schemas.user import UserCreate, DeleteRequestUser
from schemas.config import ConfigInfoResponse
from database.repository import (
    UserRepository,
    ConfigRepository,

)
from database.database import get_db
from dependencies import (
    get_user_repo,
    get_config_repo,
)
from utils.config import delete_config


router = APIRouter()


@router.post("/create_user/")
async def create_user_view(
    user_data: UserCreate,
    user_repo: UserRepository = Depends(get_user_repo)
):
    try:
        user = user_repo.create(user_id=user_data.user_id)
        if user:
            return {"status": "created"}
        raise HTTPException(status_code=400, detail="User already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/delete_user/')
async def delete_user(
    data: DeleteRequestUser,
    db: Session = Depends(get_db)
):
    await delete_config(
        user_id=data.user_id,
        config_name=data.config_name,
        db=db
    )
    return {'delete': 'OK'}


@router.get("/{user_id}/")
async def get_user(
    user_id: int,
    user_repo: UserRepository = Depends(get_user_repo)
):
    user = user_repo.get_by_id(user_id)
    if user:
        return user
    raise HTTPException(status_code=404, detail="User not created")


@router.get("/{user_id}/configs/")
async def get_user_configs(
    user_id: int,
    config_repo: ConfigRepository = Depends(get_config_repo)
):
    configs = config_repo.get_by_user(user_id)
    return [ConfigInfoResponse(
        id=c.id,
        config_name=c.config_name,
        created_at=c.created_at,
        expires_at=c.expires_at
    ) for c in configs]


@router.post("/send_notification/")
async def send_notification(
    user_id: int,
    text: str,
    user_repo: UserRepository = Depends(get_user_repo)
):
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    message = {
        "user_id": user_id,
        "text": text
    }

    from utils.rabbitmq import RabbitMq
    success = await RabbitMq.publish_message(message)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send notification")

    return {"status": "Notification sent"}
