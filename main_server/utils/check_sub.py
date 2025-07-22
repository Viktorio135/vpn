import logging
import datetime


from sqlalchemy.orm import Session


from database.database import get_db
from database.repository import ConfigRepository
from utils.rabbitmq import RabbitMq
from utils.config import delete_config


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_sub():
    db: Session = next(get_db())
    configs = ConfigRepository(db).get_all()
    for config in configs:
        if config.expires_at and config.expires_at < datetime.datetime.now():
            await RabbitMq.publish_message(
                {
                    "user_id": config.user_id,
                    "text": f"Ваш конфиг {config.config_name} истек.",
                },
            )
            logger.info(f"Config {config.config_name} expired for user {config.user_id}.")
            if not await delete_config(
                user_id=config.user_id,
                config_name=config.config_name,
                db=db
            ):
                logger.info(f"Failed to delete expired config {config.config_name} for user {config.user_id}.")
        elif config.expires_at and config.expires_at < datetime.datetime.now() + datetime.timedelta(days=3):
            remaining_days = (config.expires_at - datetime.datetime.now()).days
            await RabbitMq.publish_message(
                {
                    "user_id": config.user_id,
                    "text": f"Ваш конфиг {config.config_name} истекает через {remaining_days} дня. Пожалуйста, продлите его.",
                }
            )
