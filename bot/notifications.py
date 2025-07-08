import aio_pika
import json
import logging


from rabbitmq import RabbitMQ

logger = logging.getLogger(__name__)


async def process_notification(message: aio_pika.IncomingMessage):
    try:
        async with message.process():
            payload = json.loads(message.body.decode())
            user_id = payload.get('user_id')
            text = payload.get('text')

            if not user_id or not text:
                logger.error("Invalid notification payload")
                return

            from bot import bot

            await bot.send_message(chat_id=user_id, text=text)
            logger.info(f"Notification sent to user {user_id}")
    except Exception as e:
        logger.error(f"Error processing notification: {e}")


async def start_rabbit_consumer():
    await RabbitMQ.consume_messages(process_notification)
