import aio_pika
import json
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class RabbitMQ:
    _connection = None
    _channel = None
    _queue = None

    @classmethod
    async def get_connection(cls):
        if cls._connection is None or cls._connection.is_closed:
            rabbitmq_url = os.getenv('RABBITMQ_URL')
            cls._connection = await aio_pika.connect_robust(rabbitmq_url)
        return cls._connection

    @classmethod
    async def get_channel(cls):
        if cls._channel is None or cls._channel.is_closed:
            connection = await cls.get_connection()
            cls._channel = await connection.channel()
        return cls._channel

    @classmethod
    async def get_queue(cls):
        if cls._queue is None:
            channel = await cls.get_channel()
            queue_name = os.getenv('NOTIFICATION_QUEUE', 'bot_notifications')
            cls._queue = await channel.declare_queue(queue_name, durable=True)
        return cls._queue

    @classmethod
    async def publish_message(cls, message: dict):
        try:
            channel = await cls.get_channel()
            queue = await cls.get_queue()
            message_body = json.dumps(message).encode()
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=message_body,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=queue.name
            )
            logger.info(f"Message published to RabbitMQ: {message}")
            return True
        except Exception as e:
            logger.error(f"Error publishing to RabbitMQ: {e}")
            return False

    @classmethod
    async def consume_messages(cls, callback):
        try:
            queue = await cls.get_queue()
            await queue.consume(callback)
            logger.info("Started consuming messages from RabbitMQ")
        except Exception as e:
            logger.error(f"Error consuming messages: {e}")
