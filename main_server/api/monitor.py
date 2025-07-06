from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.database import get_db
from database.repository import ServerRepository
from dependencies import get_server_repo

router = APIRouter()


@router.post('/statuses/')
async def get_statuses(
    db: Session = Depends(get_db),
    server_repo: ServerRepository = Depends(get_server_repo)
):
    servers = server_repo.get_all_active()
    response = {}
    for server in servers:
        response[server.ip] = {
            'cpu': server.cpu_percent,
            'ram': server.memory_usage,
            'sent_traffic': server.sent_traffic,
            'recv_traffic': server.recv_traffic
        }
    return response
