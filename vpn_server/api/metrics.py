import psutil
import time

from fastapi import APIRouter, Response
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST

router = APIRouter()

CPU_USAGE = Gauge('server_cpu_usage_percent', 'CPU usage percent')
MEM_USAGE = Gauge('server_memory_usage_percent', 'Memory usage percent')
BYTES_SENT = Gauge('server_bytes_sent_per_sec', 'Bytes sent per second')
BYTES_RECV = Gauge('server_bytes_recv_per_sec', 'Bytes received per second')

prev_net_io = psutil.net_io_counters()
prev_time = time.time()


@router.get("")
async def metrics():
    global prev_net_io, prev_time

    CPU_USAGE.set(psutil.cpu_percent(interval=0.1))
    MEM_USAGE.set(psutil.virtual_memory().percent)

    current_net_io = psutil.net_io_counters()
    current_time = time.time()

    bytes_sent = current_net_io.bytes_sent - prev_net_io.bytes_sent
    bytes_recv = current_net_io.bytes_recv - prev_net_io.bytes_recv
    time_diff = current_time - prev_time

    if time_diff > 0:
        BYTES_SENT.set(bytes_sent / time_diff)
        BYTES_RECV.set(bytes_recv / time_diff)

    prev_net_io = current_net_io
    prev_time = current_time

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
