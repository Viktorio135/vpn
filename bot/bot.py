import json
import os
import httpx
import uuid

from dotenv import load_dotenv
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    FSInputFile,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from pydantic import BaseModel
from aiosend import CryptoPay, TESTNET
from aiosend.types import Invoice

load_dotenv()

# Настройки
API_BASE_URL = os.getenv('API_BASE_URL')
BOT_TOKEN = os.getenv('TOKEN')
CRYPTO_BOT_TOKEN = os.getenv('CRYPTO_BOT_TOKEN')

bot = Bot(token=BOT_TOKEN)
pay = CryptoPay(CRYPTO_BOT_TOKEN, TESTNET)
dp = Dispatcher()


class ConfigInfo(BaseModel):
    id: int
    config_name: str
    created_at: str
    expires_at: str


async def api_request(method: str, endpoint: str, data: dict = None):
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        try:
            response = await client.request(method, endpoint, json=data)
            response.raise_for_status()
            return response.json(), response.status_code
        except httpx.HTTPStatusError as e:
            print(f"API error: {e}")
            return None


async def create_new_conf(data: dict):
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        try:
            response = await client.request(
                "POST", "/get_available_server/", json=data
            )
            response.raise_for_status()
            return response.content, response.status_code
        except httpx.HTTPStatusError as e:
            print(f"API error: {e}")
            return None


async def get_conf_data(config_id: int, data: dict = None):
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        try:
            response = await client.request("POST", f"/config/{config_id}/")
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            print(f"API error: {e}")
            return None


@dp.message(Command("start"))
async def start_handler(msg: Message):
    user_id = msg.from_user.id
    user, status_code = await api_request(
            "GET",
            f"/user/{user_id}/",
        )
    if user["status_code"] == 200:
        await msg.answer(
            "Вы попали в главное меню!",
            reply_markup=main_menu()
        )
    else:
        await api_request("POST", "/create_user/", {"user_id": user_id})

        # Создаем бесплатную конфигурацию
        try:
            await create_new_conf(
                data={
                    "user_id": user_id,
                    "config_name": "default",
                    "months": 0  # Для 5 дней нужно добавить логику в бэкенд
                }
            )
        except Exception as e:
            print(f"Error creating config: {e}")

        await msg.answer(
            "🎉 Добро пожаловать! Вам активирована бесплатная подписка на 5 дней.",
            reply_markup=main_menu()
        )


def main_menu():
    buttons = [
        [KeyboardButton(text="📁 Мои конфигурации")],
        [KeyboardButton(text="💳 Приобрести/продлить")],
        [KeyboardButton(text="❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


@dp.message(F.text == '📁 Мои конфигурации')
async def show_configs(message: types.Message):
    user_id = message.from_user.id
    configs, status_code = await api_request(
        "GET", f"/user/{user_id}/configs/"
    )

    if not configs:
        await bot.send_message(
            message.from_user.id,
            "У вас пока нет конфигураций.",
            reply_markup=main_menu()
        )
        return

    builder = InlineKeyboardBuilder()
    for config in configs:
        builder.add(InlineKeyboardButton(
            text=config['config_name'],
            callback_data=f"config_{config['id']}"
        ))
    builder.adjust(1)

    await bot.send_message(
        message.from_user.id,
        "Ваши конфигурации:",
        reply_markup=builder.as_markup()
    )


@dp.callback_query(F.data.startswith("config_"))
async def config_detail(callback: types.CallbackQuery, bot: Bot):
    config_id = int(callback.data.split("_")[1])
    file_content = await get_conf_data(config_id)

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


@dp.callback_query(F.data.startswith("renew_"))
async def renew_config(callback: types.CallbackQuery):
    config_id = int(callback.data.split("_")[1])
    # Логика продления через API
    await callback.answer("Функция продления в разработке")


@dp.callback_query(F.data == "buy_renew")
async def buy_renew_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    configs, status_code = await api_request(
        "GET", f"/user/{user_id}/configs/"
    )

    builder = InlineKeyboardBuilder()
    for config in configs:
        builder.add(InlineKeyboardButton(
            text=f"Продлить {config['config_name']}",
            callback_data=f"renew_{config['id']}"
        ))
    builder.add(InlineKeyboardButton(
        text="Купить новую конфигурацию",
        callback_data="buy_new"
    ))
    builder.adjust(1)

    await callback.message.edit_text(
        "Выберите действие:",
        reply_markup=builder.as_markup()
    )


@dp.callback_query(F.data == "help")
async def show_help(callback: types.CallbackQuery):
    help_text = (
        "📖 Инструкция по настройке WireGuard:\n\n"
        "1. Скачайте и установите клиент WireGuard\n"
        "2. Импортируйте конфигурационный файл\n"
        "3. Активируйте подключение\n"
        "4. Готово! Ваш трафик защищен 🔒"
    )
    await callback.message.edit_text(
        help_text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(
                text="Назад", callback_data="back_to_main"
            )]]
        )
    )


@pay.invoice_polling()
async def handle_payment(invoice: Invoice, message: types.Message, data: list):
    if invoice.status == "paid":
        config_name = str(uuid.uuid4())
        file, status_code = await create_new_conf(data={
            "user_id": data["user_id"],
            "config_name": config_name,
            "months": data["days"]
        })
        if int(status_code) == 200:
            file_name = f"{data['user_id']}_{config_name}.conf"
            with open(file_name, "wb") as f:
                f.write(file)

            # Отправляем файл пользователю
            file = FSInputFile(file_name)
            await message.answer_document(
                document=file,
                caption="✅ Оплата прошла успешно! Ваша новая конфигурация:"
            )

            # Удаляем временный файл
            os.remove(file_name)
        else:
            await bot.send_message(
                message.from_user.id,
                'Что-то пошло не так('
            )


@dp.message(F.text == '💳 Приобрести/продлить')
async def show_payment_options(message: types.Message):
    builder = InlineKeyboardBuilder()

    # Добавляем варианты подписок
    subscriptions = [
        ("1 месяц - 1.5 USDT", 30),
        ("3 месяца - 2.5 USDT", 90),
        ("6 месяцев - 4 USDT", 180)
    ]

    for name, days in subscriptions:
        builder.add(InlineKeyboardButton(
            text=name,
            callback_data=f"subscribe_{days}"
        ))

    builder.adjust(1)
    await message.answer(
        "Выберите тарифный план:",
        reply_markup=builder.as_markup()
    )


@dp.callback_query(F.data.startswith("subscribe_"))
async def process_payment(callback: types.CallbackQuery):
    days = int(callback.data.split("_")[1])
    amount = {
        30: 15,
        90: 25,
        180: 40
    }.get(days, 5)

    invoice = await pay.create_invoice(
        amount, "USDT"
    )
    invoice.poll(message=callback.message, data={
        'user_id': callback.from_user.id,
        'days': days
    })

    await callback.message.answer(
        f"💸 Оплатите {amount} USDT через криптобота:\n"
        f"<a href='{invoice.bot_invoice_url}'>Ссылка для оплаты</a>\n\n",
        parse_mode="HTML"
    )


# @dp.callback_query(F.data.startswith("confirm_payment_"))
# async def confirm_payment(callback: types.CallbackQuery):
#     days = int(callback.data.split("_")[2])
#     user_id = callback.from_user.id

#     # Здесь должна быть проверка оплаты через API криптобота
#     # Временно эмулируем успешную оплату

#     result = await api_request("POST", "/get_available_server/", {
#         "user_id": user_id,
#         "config_name": str(uuid.uuid4()),
#         "months": days
#     })

#     if result[1] == 200:
#         await callback.message.answer("✅ Подписка успешно активирована!")
#         await show_configs(callback.message)
#     else:
#         await callback.message.answer("❌ Ошибка активации подписки")
@dp.message(F.text == "❓ Помощь")
async def show_help_main(message: types.Message):
    help_text = (
        "📖 Инструкция по настройке WireGuard:\n\n"
        "1. Скачайте и установите клиент WireGuard\n"
        "2. Импортируйте конфигурационный файл\n"
        "3. Активируйте подключение\n"
        "4. Готово! Ваш трафик защищен 🔒"
    )
    await bot.send_message(
        message.from_user.id,
        help_text,
    )


async def main():
    await asyncio.gather(
        dp.start_polling(bot),
        pay.start_polling()
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
