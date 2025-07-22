import os

from fastapi import FastAPI
from pathlib import Path
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler


from dotenv import load_dotenv
from database.database import engine
from database.models import Base
from utils.monitor import monitor_vpn_servers
from utils.check_sub import check_sub
from middlewares import VerifyMiddleware
from api.config import router as config_router
from api.monitor import router as monitor_router
from api.server import router as server_router
from api.user import router as user_router
from api.auth import router as auth_router
from api.transaction import router as transaction_router
from api.postback import router as postback_router


load_dotenv()


CONFIGS_DIR = Path("./confs")
CONFIGS_DIR.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(monitor_vpn_servers, 'interval', minutes=5)
    scheduler.add_job(check_sub, 'interval', seconds=20)
    scheduler.start()

    os.makedirs("./public_keys", exist_ok=True)

    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)

app.add_middleware(VerifyMiddleware)

app.include_router(config_router, prefix="/config", tags=["config"])
app.include_router(monitor_router, prefix="/monitor", tags=["monitor"])
app.include_router(server_router, prefix="/server", tags=["server"])
app.include_router(user_router, prefix="/user", tags=["user"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(transaction_router, prefix="/transaction", tags=["transaction"])
app.include_router(postback_router, prefix="/postback", tags=["postback"])
