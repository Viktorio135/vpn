import subprocess
import logging


from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse


from dependencies import get_ip_repository, get_client_repository
from database.repository import IPRepository, ClientRepository
from core.wg import (
    generate_keys,
    add_client_to_server_config,
    delete_client_from_server_config,
)
from schemas.client import CreateClientRequest, DeleteClientRequest


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


router = APIRouter()


@router.post("/generate-config/")
async def generate_config(
    request: CreateClientRequest,
    ip_repo: IPRepository = Depends(get_ip_repository),
    client_repo: ClientRepository = Depends(get_client_repository)
):

    from main_vpn import (
        DNS,
        SERVER_PUBLIC_KEY,
        SERVER_ENDPOINT,
        CONFIGS_DIR,
    )

    # Генерируем ключи
    private_key, public_key = generate_keys()

    # Выделяем IP
    client_ip = ip_repo.get_free_ip()
    if not client_ip:
        raise HTTPException(400, "Нет свободных IP-адресов")
    ip_repo.mark_ip_used(client_ip, request.user_id)

    # Создаем конфиг клиента
    config = f"""[Interface]
PrivateKey = {private_key}
Address = {client_ip.address}/24
DNS = {DNS}

[Peer]
PublicKey = {SERVER_PUBLIC_KEY}
Endpoint = {SERVER_ENDPOINT}:443
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""

    config_filename = f"{request.user_id}_{request.config_name}.conf"
    config_path = CONFIGS_DIR / config_filename
    logger.info(f"Сохраняем конфиг клиента: {config}")
    with open(config_path, "w") as f:
        f.write(config)

    # Добавляем клиента на сервер
    try:
        add_client_to_server_config(public_key, client_ip.address)
    except subprocess.CalledProcessError:
        raise HTTPException(500, "Ошибка добавления клиента")

    # Сохраняем в бд
    client = client_repo.create(
        client_id=request.user_id,
        private_key=private_key,
        public_key=public_key,
        ip_address=client_ip.id,
        config_name=request.config_name
    )
    if not client:
        raise HTTPException(500, "Ошибка создания клиента")

    return FileResponse(
        path=config_path,
        filename=config_filename,
        media_type="application/octet-stream"
    )


@router.post("/delete-config/")
async def delete_config(
    request: DeleteClientRequest,
    ip_repo: IPRepository = Depends(get_ip_repository),
    client_repo: ClientRepository = Depends(get_client_repository)
):

    from main_vpn import (
        CONFIGS_DIR,
    )

    # Получаем клиента из БД
    client = client_repo.get_by_id_and_name(
        request.user_id, request.config_name
    )
    if not client:
        logger.error(f"Клиент с user_id {request.user_id} и config_name {request.config_name} не найден")
        raise HTTPException(404, "Клиент не найден")

    ip = ip_repo.db.query(ip_repo.model).filter_by(id=client.ip_address).first()
    if not ip:
        logger.error(f"IP-адрес для клиента {client.public_key} не найден")
        raise HTTPException(404, "IP-адрес не найден")

    try:
        delete_client_from_server_config(client.public_key)
    except subprocess.CalledProcessError:
        raise HTTPException(500, "Ошибка настройки сервера")

    # Удаляем клиента из БД и освобождаем IP
    client_repo.delete(client)
    ip_repo.free_ip(ip)

    # Удаляем файл конфига
    config_filename = f"{request.user_id}_{request.config_name}.conf"
    config_path = CONFIGS_DIR / config_filename
    if config_path.exists():
        config_path.unlink()

    return {"status": "success"}
