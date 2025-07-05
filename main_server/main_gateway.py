from fastapi import FastAPI
from pathlib import Path
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler


from dotenv import load_dotenv
from main_server.database.database import engine
from main_server.database.models import Base
from utils.monitor import monitor_vpn_servers
from api.config import router as config_router
from api.monitor import router as monitor_router
from api.server import router as server_router
from api.user import router as user_router


load_dotenv()


CONFIGS_DIR = Path("./confs")
CONFIGS_DIR.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    scheduler = BackgroundScheduler()
    scheduler.add_job(monitor_vpn_servers, 'interval', minutes=5)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)

app.include_router(config_router, prefix="/config", tags=["config"])
app.include_router(monitor_router, prefix="/monitor", tags=["monitor"])
app.include_router(server_router, prefix="/server", tags=["server"])
app.include_router(user_router, prefix="/user", tags=["user"])


