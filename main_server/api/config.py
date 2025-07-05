import json


from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session


from main_gateway import CONFIGS_DIR
from main_server.database.database import get_db
from main_server.database.repository import WGConfigRepository
from dependencies import get_config_repo


router = APIRouter()


@router.post("/{config_id}/")
async def get_config(
    config_id: int,
    repo: WGConfigRepository = Depends(get_config_repo)
):
    config = repo.get_by_id(config_id)
    if config:
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
    months: int,
    repo: WGConfigRepository = Depends(get_config_repo),
    db: Session = Depends(get_db),
):
    config = repo.get_by_id(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    repo.add_expires(config_id, months)
    return {"status": "renewed", "new_expires": config.expires_at}
