import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from fastapi.exceptions import HTTPException


from database.repository import ConfigRepository
from dependencies import get_config_repo
from schemas.config import RenewRequest


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


router = APIRouter()


@router.post("/{config_id}/")
async def get_config(
    config_id: int,
    repo: ConfigRepository = Depends(get_config_repo)
):
    config = repo.get_by_id(config_id)
    if config:
        from main_gateway import CONFIGS_DIR
        config_path = (
            CONFIGS_DIR / f"{config.user_id}_{config.config_name}.conf"
        )
        data = {
            "config_name": config.config_name,
            "created_at": str(config.created_at),
            "expires_at": str(config.expires_at),
        }
        return FileResponse(
            config_path,
            filename=f"{config.user_id}_{config.config_name}.conf",
            headers={
                "X-Data": json.dumps(data)
            }
        )
    return HTTPException(status_code=404, detail="Config not found")


@router.post("/{config_id}/renew/")
async def renew_config(
    config_id: int,
    body: RenewRequest,
    repo: ConfigRepository = Depends(get_config_repo),
):
    months = body.months
    try:
        config = repo.get_by_id(config_id)
        if not config:
            raise HTTPException(status_code=404, detail="Config not found")

        repo.add_expires(config_id, months)
        return {"status": "renewed", "new_expires": config.expires_at}
    except Exception as e:
        logger.error(f"Error renewing config {config_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
