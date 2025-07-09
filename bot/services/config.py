import json
import os


from datetime import datetime

from aiogram import Bot, types
from aiogram.types import FSInputFile
from utils.api import get_conf_data


async def send_config(
        callback: types.CallbackQuery,
        bot: Bot,
        config_id: int
):
    file_content, status_code = await get_conf_data(config_id)

    # Извлекаем заголовки
    headers = json.loads(file_content.headers['x-data'])

    # Получаем содержимое файла
    file_content = file_content.content

    # Сохраняем файл на диск
    file_name = f"{callback.from_user.id}_{headers['config_name']}.conf"
    with open(file_name, "wb") as file:
        if isinstance(file_content, str):
            file.write(file_content.encode())
        else:
            file.write(file_content)  # Если это байты, записываем напрямую

    # Форматируем даты
    created_at_data_obj = datetime.fromisoformat(headers['created_at'])
    expires_at_data_obj = datetime.fromisoformat(headers['expires_at'])

    # Текст сообщения
    text = (
        f"🔐 Конфигурация: {headers['config_name']}\n"
        f"📅 Создана: {created_at_data_obj.strftime('%d.%m.%Y %H:%M:%S')}\n"
        f"⏳ Истекает: {expires_at_data_obj.strftime('%d.%m.%Y %H:%M:%S')}"
    )

    # Кнопки
    buttons = [
        [types.InlineKeyboardButton(
            text="Продлить", callback_data=f"renew_{config_id}"
        )],
        [types.InlineKeyboardButton(
            text="Переустановить", callback_data=f"reinstall_{config_id}"
        )],
    ]

    # Создаем FSInputFile для отправки файла
    file = FSInputFile(file_name)

    # Отправляем файл пользователю
    await bot.send_document(
        chat_id=callback.message.chat.id,
        document=file,
        caption=text,
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons)
    )

    os.remove(file_name)
