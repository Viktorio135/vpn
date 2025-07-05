from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from main_server.database.database import get_db
from database.models import ServerRepository
from dependencies import get_server_repo

router = APIRouter()


@router.post('/statuses/')
async def get_statuses(
    db: Session = Depends(get_db),
    server_repo: ServerRepository = Depends(get_server_repo)
):
    servers = server_repo.get_all()
    response = {}
    for server in servers:
        response[server.ip] = {
            'cpu': server.cpu_percent,
            'ram': server.memory_usage,
            'sent_traffic': server.sent_traffic,
            'recv_traffic': server.recv_traffic
        }
    return response
