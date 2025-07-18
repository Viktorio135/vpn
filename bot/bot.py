import json
import os
import time
import httpx
import uuid
import re
import logging

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    FSInputFile,
    KeyboardButton,
    ReplyKeyboardMarkup,
    LabeledPrice,
    PreCheckoutQuery
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from pydantic import BaseModel
from aiosend import CryptoPay, TESTNET
from aiosend.types import Invoice
from tronpy.providers import HTTPProvider


from utils.api import (
    api_request,
    create_new_conf,
    renew_conf,
    reinstall_conf
)
from utils.register import register
from states import PaymentState, RenewState
from notifications import start_rabbit_consumer
from services.config import send_config


load_dotenv('/Users/viktorshpakovskij/Step/vpn/.env')

# Настройки
API_BASE_URL = os.environ.get('API_BASE_URL')
BOT_TOKEN = os.environ.get('TOKEN')
CRYPTO_BOT_TOKEN = os.environ.get('CRYPTO_BOT_TOKEN')


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


bot = Bot(token=BOT_TOKEN)
pay = CryptoPay(CRYPTO_BOT_TOKEN, TESTNET)
dp = Dispatcher()


TRONGRID_API_KEY = os.getenv('TRONGRID_API_KEY')
TRON_PROVIDER = HTTPProvider(api_key=TRONGRID_API_KEY)
TRON_NETWORK = os.getenv('TRON_NETWORK', 'nile')
USDT_CONTRACT_ADDRESS = os.getenv('USDT_CONTRACT_ADDRESS')
DEPOSIT_ADDRESS = os.getenv('DEPOSIT_ADDRESS')


class ConfigInfo(BaseModel):
    id: int
    config_name: str
    created_at: str
    expires_at: str


@dp.message(Command("start"))
async def start_handler(msg: Message):
    user_id = msg.from_user.id
    user, status_code = await api_request(
            "GET",
            f"/user/{user_id}/",
        )
    if status_code == 200:
        await msg.answer(
            "Вы попали в главное меню!",
            reply_markup=main_menu()
        )
    else:
        await api_request("POST", "/user/create_user/", {"user_id": user_id})

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
        [KeyboardButton(text="💳 Приобрести")],
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
    await send_config(callback, bot, config_id)


@dp.callback_query(F.data.startswith("reinstall_"))
async def reinstall_config(callback: types.CallbackQuery):
    config_id = int(callback.data.split("_")[1])
    try:
        new_config, status_code = await reinstall_conf(config_id)
        if status_code == 200:
            await callback.message.answer(
                "✅ Конфигурация успешно переустановлена!",
            )
            print(new_config)
            await send_config(callback, bot, new_config['config_id'])
        else:
            await callback.message.answer(
                "❌ Ошибка переустановки конфигурации. Обратитесь в поддержку."
            )
    except Exception as e:
        logger.error(f"Ошибка переустановки конфигурации {config_id}: {e}")
        await callback.message.answer(
            "🚨 Критическая ошибка системы. Мы уже работаем над исправлением."
        )


@dp.callback_query(lambda c: c.data.startswith("renew_") and c.data.split("_")[1].isdigit())
async def renew_config(callback: types.CallbackQuery, state: FSMContext):
    config_id = int(callback.data.split("_")[1])
    await state.update_data(config_id=config_id)
    builder = InlineKeyboardBuilder()
    periods = [
        ("1 месяц - 1.5 USDT", 1),
        ("3 месяца - 2.5 USDT", 3),
        ("6 месяцев - 4 USDT", 6)
    ]
    for name, months in periods:
        builder.add(InlineKeyboardButton(
            text=name,
            callback_data=f"renewperiod_{months}"
        ))
    builder.adjust(1)
    await callback.message.answer(
        "Выберите срок продления:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(RenewState.CHOOSE_PERIOD)


@dp.callback_query(RenewState.CHOOSE_PERIOD, F.data.startswith("renewperiod_"))
async def renew_choose_method(callback: types.CallbackQuery, state: FSMContext):
    months = int(callback.data.split("_")[1])
    amount = {
        1: 1.5,
        3: 2.5,
        6: 4.0
    }.get(months, 1.5)
    await state.update_data(months=months, amount=amount)
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="CryptoBot", callback_data="renewmethod_crypto"),
        InlineKeyboardButton(text="TRC20 (0% комиссий)", callback_data="renewmethod_tron")
    )
    await callback.message.answer(
        "Выберите способ оплаты:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(RenewState.CHOOSE_METHOD)


@dp.callback_query(RenewState.CHOOSE_METHOD, F.data.startswith("renewmethod_"))
async def renew_payment_method(callback: types.CallbackQuery, state: FSMContext):
    method = callback.data.split("_")[1]
    data = await state.get_data()
    if method == "crypto":
        invoice = await pay.create_invoice(data['amount'], "USDT")
        invoice.poll(message=callback.message, data={
            'user_id': callback.from_user.id,
            'config_id': data['config_id'],
            'months': data['months'],
            'renew': True
        })
        await callback.message.answer(
            f"💸 Оплатите {data['amount']} USDT:\n"
            f"<a href='{invoice.bot_invoice_url}'>Ссылка для оплаты</a>",
            parse_mode="HTML"
        )
        await state.clear()
    elif method == "tron":
        await callback.message.answer(
            "Введите ваш TRC20-адрес USDT для проверки транзакции:"
        )
        await state.set_state(RenewState.AWAITING_WALLET)


@dp.message(RenewState.AWAITING_WALLET)
async def renew_tron_wallet(message: Message, state: FSMContext):
    if not re.match(r'^T[1-9A-HJ-NP-Za-km-z]{33}$', message.text):
        await message.answer("❌ Неверный формат кошелька! Попробуйте снова:")
        return
    await state.update_data(wallet=message.text)
    await state.update_data(start_time=int(time.time() * 1000))
    data = await state.get_data()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я перевел", callback_data="renew_check_tron")]
    ])
    await message.answer(
        f"📥 Отправьте <b>{data['amount']} USDT</b> на адрес:\n"
        f"<code>{DEPOSIT_ADDRESS}</code>\n\n"
        "После отправки нажмите кнопку ниже для проверки.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(RenewState.AWAITING_PAYMENT)

@dp.callback_query(RenewState.AWAITING_PAYMENT, F.data.in_(["renew_check_tron", "renew_recheck_tron"]))
async def renew_check_tron_payment(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback.message.edit_reply_markup()
    try:
        result = await check_tron_transaction(
            sender=data['wallet'],
            amount=data['amount'],
            min_timestamp=data['start_time']
        )
        if result['status'] == 'success':
            renew_result, status_code = await renew_conf(
                config_id=data['config_id'],
                months=data['months']
            )
            if status_code == 200:
                await callback.message.answer(
                    f"✅ Конфигурация успешно продлена!\n"
                    f"Хэш транзакции: {result['tx_hash']}\n"
                    f"Сумма: {result['amount']} USDT"
                )
            else:
                await callback.message.answer("❌ Ошибка продления. Обратитесь в поддержку.")
        elif result['status'] == 'not_found':
            retry_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Проверить ещё раз", callback_data="renew_recheck_tron")]
            ])
            await callback.message.answer(
                "⚠️ Платеж не обнаружен. Проверьте детали и попробуйте ещё раз.",
                reply_markup=retry_kb
            )
        else:
            await callback.message.answer(f"🚨 Ошибка проверки: {result['message']}")
    except Exception as e:
        await callback.message.answer("🚨 Критическая ошибка системы. Мы уже работаем над исправлением.")


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
async def handle_payment(invoice: Invoice, message: types.Message, data: dict):
    if invoice.status == "paid":
        if data.get('renew'):
            # Продление существующей конфигурации
            renew_result, status_code = await renew_conf(
                config_id=data['config_id'],
                months=data['months']
            )
            if status_code == 200:
                await message.answer("✅ Конфигурация успешно продлена!")
            else:
                await message.answer("❌ Ошибка продления. Обратитесь в поддержку.")
        else:
            # Покупка новой конфигурации
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
                file = FSInputFile(file_name)
                await message.answer_document(
                    document=file,
                    caption="✅ Оплата прошла успешно! Ваша новая конфигурация:"
                )
                os.remove(file_name)
            else:
                await message.answer('Что-то пошло не так(')



@dp.message(F.text == '💳 Приобрести')
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
async def process_payment(callback: types.CallbackQuery, state: FSMContext):
    days = int(callback.data.split("_")[1])
    amount = {
        30: 1.5,
        90: 2.5,
        180: 4.0
    }.get(days, 0.5)

    await state.update_data(days=days, amount=amount)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="CryptoBot", callback_data="method_crypto")
    ).row(
        InlineKeyboardButton(text="TRC20 (0% комиссий)", callback_data="method_tron")
    ).row(
        InlineKeyboardButton(text="Звезды Telegram", callback_data="method_stars")
    )

    await callback.message.answer(
        "Выберите способ оплаты:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(PaymentState.CHOOSE_METHOD)


# Обработчик выбора метода оплаты
@dp.callback_query(PaymentState.CHOOSE_METHOD, F.data.startswith("method_"))
async def handle_payment_method(callback: types.CallbackQuery, state: FSMContext):
    method = callback.data.split("_")[1]
    data = await state.get_data()

    if method == "crypto":
        invoice = await pay.create_invoice(data['amount'], "USDT")
        invoice.poll(message=callback.message, data={
            'user_id': callback.from_user.id,
            'days': data['days']
        })
        await callback.message.answer(
            f"💸 Оплатите {data['amount']} USDT:\n"
            f"<a href='{invoice.bot_invoice_url}'>Ссылка для оплаты</a>",
            parse_mode="HTML"
        )
        await state.clear()

    elif method == "tron":
        await callback.message.answer(
            "Введите ваш TRC20-адрес USDT для проверки транзакции:"
        )
        await state.set_state(PaymentState.AWAITING_WALLET)

    elif method == "stars":
        stars_price = {
            30: 75,
            90: 110,
            180: 200
        }
        days = data['days']
        price = [LabeledPrice(label="XTR", amount=stars_price[days])]
        # price = [LabeledPrice(label="XTR", amount=1)]
        builder = InlineKeyboardBuilder()
        builder.button(text=f'Оплатить {stars_price[days]} звезд', pay=True)

        await callback.message.answer_invoice(
            title="Оплата подписки",
            description=f"Оплатить подписку за {stars_price[days]} звезд",
            prices=price,
            provider_token="",
            currency="XTR",
            reply_markup=builder.as_markup(),
            payload=json.dumps({
                "user_id": callback.from_user.id,
                "days": days
            })
        )
        await state.clear()


@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@dp.message(F.successful_payment)
async def success_payment_handler(message: Message):
    payload = json.loads(message.successful_payment.invoice_payload)
    config_name = str(uuid.uuid4())
    file, status_code = await create_new_conf(data={
        "user_id": payload["user_id"],
        "config_name": config_name,
        "months": payload["days"]
    })
    if int(status_code) == 200:
        file_name = f"{payload['user_id']}_{config_name}.conf"
        with open(file_name, "wb") as f:
            f.write(file)
        file = FSInputFile(file_name)
        await message.answer_document(
            document=file,
            caption="✅ Оплата прошла успешно! Ваша новая конфигурация:"
        )
        os.remove(file_name)
    else:
        await message.answer('Что-то пошло не так(')


# Обработчик TRC20 адреса
@dp.message(PaymentState.AWAITING_WALLET)
async def process_tron_wallet(message: Message, state: FSMContext):
    if not re.match(r'^T[1-9A-HJ-NP-Za-km-z]{33}$', message.text):
        await message.answer("❌ Неверный формат кошелька! Попробуйте снова:")
        return

    await state.update_data(wallet=message.text)
    await state.update_data(start_time=int(time.time() * 1000))
    data = await state.get_data()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я перевел", callback_data="check_tron")]
    ])

    await message.answer(
        f"📥 Отправьте <b>{data['amount']} USDT</b> на адрес:\n"
        f"<code>{DEPOSIT_ADDRESS}</code>\n\n"
        "После отправки нажмите кнопку ниже для проверки.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(PaymentState.AWAITING_PAYMENT)


async def check_tron_transaction(sender: str, amount: float, min_timestamp: int) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://nile.trongrid.io/v1/accounts/{DEPOSIT_ADDRESS}/transactions/trc20",
                params={
                    "limit": 50,
                    "contract_address": USDT_CONTRACT_ADDRESS,
                    "only_confirmed": "true",
                    "order_by": "block_timestamp,desc"
                },
                headers={"TRON-PRO-API-KEY": TRONGRID_API_KEY}
            )

            transactions = response.json().get('data', [])
            for tx in transactions:
                if (
                    tx['from'] == sender and
                    tx['to'] == DEPOSIT_ADDRESS and
                    float(tx['value']) / 1_000_000 >= amount - 0.1 and
                    tx['block_timestamp'] >= min_timestamp
                ):
                    return {
                        'status': 'success',
                        'tx_hash': tx['transaction_id'],
                        'amount': float(tx['value']) / 1_000_000
                    }

            return {'status': 'not_found'}

    except Exception as e:
        print(f"TRON API error: {e}")
        return {'status': 'error', 'message': str(e)}


# Обработчик проверки платежа
@dp.callback_query(PaymentState.AWAITING_PAYMENT, F.data.in_(["check_tron", "recheck_tron"]))
async def check_tron_payment(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback.message.edit_reply_markup()

    try:
        result = await check_tron_transaction(
            sender=data['wallet'],
            amount=data['amount'],
            min_timestamp=data['start_time']
        )

        if result['status'] == 'success':
            if abs(result['amount'] - data['amount']) > 0.1:
                await callback.message.answer(
                    f"⚠️ Обнаружен платеж, но сумма не совпадает!\n"
                    f"Отправлено: {result['amount']} USDT\n"
                    f"Требуется: {data['amount']} USDT\n\n"
                    "Обратитесь в поддержку."
                )
                return

            file_content, status_code = await create_new_conf({
                "user_id": callback.from_user.id,
                "config_name": str(uuid.uuid4()),
                "months": data['days']
            })

            if status_code == 200:
                file_name = f"{callback.from_user.id}.conf"
                with open(file_name, "wb") as f:
                    f.write(file_content)

                await callback.message.answer_document(
                    FSInputFile(file_name),
                    caption=(
                        "✅ Платеж подтвержден!\n"
                        f"Хэш транзакции: {result['tx_hash']}\n"
                        f"Сумма: {result['amount']} USDT\n"
                        "Ваша конфигурация:"
                    )
                )
                os.remove(file_name)
            else:
                await callback.message.answer("❌ Ошибка создания конфигурации. Обратитесь в поддержку.")
        elif result['status'] == 'not_found':
            await callback.message.answer(
                "⚠️ Платеж не обнаружен. Убедитесь, что:\n"
                "1. Вы отправили USDT на адрес\n"
                "2. Сумма и сеть TRC20 верны\n"
                "3. Прошло немного времени и транзакция подтверждена\n\n"
                "Проверку можно повторить позже.",
                parse_mode="Markdown"
            )

            # Добавим кнопку повторной проверки
            retry_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Проверить ещё раз", callback_data="recheck_tron")]
            ])
            await callback.message.answer("Хотите повторить проверку позже?", reply_markup=retry_kb)
        else:
            await callback.message.answer(f"🚨 Ошибка проверки: {result['message']}")
    except Exception as e:
        logger.error(f"Ошибка при проверке платежа: {e}")
        await callback.message.answer("🚨 Критическая ошибка системы. Мы уже работаем над исправлением.")


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
        pay.start_polling(),
        start_rabbit_consumer()
    )

if __name__ == "__main__":
    if register():
        import asyncio
        asyncio.run(main())
    else:
        logger.error('invalid registration')
        exit()
