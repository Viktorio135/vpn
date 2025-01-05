import re
import pexpect
import logging

from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel


# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Директория для хранения конфигураций
CONFIGS_DIR = Path("./clients")
CONFIGS_DIR.mkdir(exist_ok=True, parents=True)

class Filename(BaseModel):
    filename: str

def is_valid_filename(filename: str) -> bool:
    """
    Проверяет, что имя файла безопасно и не содержит недопустимых символов.
    """
    return re.match(r"^[a-zA-Z0-9_-]+$", filename) is not None


@app.post("/get_conf/")
async def get_conf(data: Filename):
    """
    Генерирует конфигурацию WireGuard для клиента.
    """
    if not is_valid_filename(data.filename):
        logger.error(f"Недопустимое имя файла: {data.filename}")
        raise HTTPException(status_code=400, detail="Недопустимое имя файла")

    try:
        child = pexpect.spawn("sudo bash wireguard-install.sh", timeout=30)

        # Ожидание запроса на выбор опции
        child.expect(re.compile(r".*Select an option:"))

        # Выбор опции "1) Add a new client"
        child.sendline("1")

        # Ожидание запроса на ввод имени клиента
        child.expect(re.compile(r".*Provide a name for the client:"))
        child.sendline(data.filename)

        # Ожидание запроса на выбор DNS
        child.expect(re.compile(r".*Select a DNS server for the client:"))
        child.sendline("1")

        # Ожидание завершения выполнения команды
        child.expect(pexpect.EOF)

        # Получение вывода
        output = child.before.decode()

        # Извлечение пути к файлу
        match = re.search(r"Configuration available in: (.*\.conf)", output)
        if not match:
            logger.error(f"Не удалось найти путь к конфигурации в выводе: {output}")
            raise HTTPException(status_code=500, detail="Ошибка при создании конфигурации")

        file_path = match.group(1)

        # Проверка существования файла
        if not Path(file_path).exists():
            logger.error(f"Файл конфигурации не найден: {file_path}")
            raise HTTPException(status_code=500, detail="Файл конфигурации не найден")
        # file_path = 'clients/mmm.txt'

        # Возвращаем файл клиенту
        return FileResponse(file_path, filename=f"{data.filename}.conf")

    except pexpect.exceptions.TIMEOUT as e:
        logger.error(f"Тайм-аут при выполнении скрипта: {e}")
        raise HTTPException(status_code=504, detail="Тайм-аут при выполнении скрипта")
    except pexpect.exceptions.EOF as e:
        logger.error(f"Скрипт завершился неожиданно: {e}")
        raise HTTPException(status_code=500, detail="Скрипт завершился неожиданно")
    except Exception as e:
        logger.error(f"Неизвестная ошибка: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")