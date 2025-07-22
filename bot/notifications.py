import aio_pika
import json
import logging


from rabbitmq import RabbitMQ
from utils.payment import get_configuration


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def process_notification(message: aio_pika.IncomingMessage):
    try:
        from bot import bot
        async with message.process():
            payload = json.loads(message.body.decode())
            if message.routing_key == 'bot_notifications':
                user_id = payload.get('user_id')
                text = payload.get('text')

                if not user_id or not text:
                    logger.error("Invalid notification payload")
                    return

                await bot.send_message(chat_id=user_id, text=text)
            elif message.routing_key == 'payment_notifications':
                status = payload.get('status')
                invoice_id = payload.get('invoice_id')
                order_id = payload.get('order_id')

                user_id = order_id.split('_')[0]
                months = int(order_id.split('_')[1])
                transaction_id = order_id.split('_')[2]

                if status == 'success':
                    await get_configuration(
                        bot=bot,
                        user_id=user_id,
                        months=months,
                        external_tx_id=invoice_id,
                        transaction_id=transaction_id
                    )

                # Process payment notification logic here
                logger.info(f"Payment notification received: {payload}")

            logger.info(f"Notification sent to user {user_id}")
    except Exception as e:
        logger.error(f"Error processing notification: {e}")


async def start_rabbit_consumer():
    await RabbitMQ.consume_messages(process_notification)
