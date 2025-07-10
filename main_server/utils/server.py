from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session


from database.repository import ServerRepository


def get_server(
        db: Session,
        exclude: list[int] = [],
):
    """
    Получаем сервер, который не в списке исключений
    :param db: сессия базы данных
    :param exclude: список исключенных серверов
    :return: сервер
    """
    server_repo = ServerRepository(db)
    servers = server_repo.get_all_active()

    if not servers:
        raise HTTPException(status_code=503, detail="Нет доступных серверов")

    for server in servers:
        if len(servers) == 1:
            return server
        if (server.id not in exclude and server.count_users < server.max_count_users):
            return server
    return None
