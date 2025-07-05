import psutil
import time


from fastapi import APIRouter
from fastapi.exceptions import HTTPException


router = APIRouter()


@router.get('')
async def get_status():
    try:
        global prev_net_io, prev_time
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory().percent

        current_net_io = psutil.net_io_counters()
        current_time = time.time()

        # Вычисляем разницу в байтах
        bytes_sent = current_net_io.bytes_sent - prev_net_io.bytes_sent
        bytes_recv = current_net_io.bytes_recv - prev_net_io.bytes_recv

        # Вычисляем разницу во времени
        time_diff = current_time - prev_time

        mb_sent = bytes_sent / (1024 * 1024)
        mb_recv = bytes_recv / (1024 * 1024)

        mb_sent_per_sec = mb_sent / time_diff
        mb_recv_per_sec = mb_recv / time_diff

        # Обновляем предыдущие значения
        prev_net_io = current_net_io
        prev_time = current_time

        return {
            "cpu": cpu,
            "memory": memory,
            "sent_traffic": mb_sent_per_sec,
            "recv_traffic": mb_recv_per_sec,
        }
    except Exception:
        raise HTTPException(
            status_code=500, detail='Ошибка в получении статуса сервера'
        )
