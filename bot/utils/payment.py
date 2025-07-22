import httpx
import uuid
import os


from dotenv import load_dotenv
from aiogram.types import FSInputFile
from aiogram import Bot


from utils.api import create_new_conf, update_transaction_status

load_dotenv()


API_KEY = os.environ.get('API_KEY')
SHOP_ID = os.environ.get('SHOP_ID')


async def create_invoice(amount: float, currency: str, order_id: str):
    url = "https://api.cryptocloud.plus/v2/invoice/create"
    headers = {
        "Authorization": f"Token {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "amount": amount,
        "shop_id": SHOP_ID,
        "currency": currency,
        "order_id": order_id,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return {
            "invoice_id": result["result"]["uuid"],
            "url": result["result"]["link"]
        }


async def get_configuration(
        bot: Bot,
        user_id: int,
        months: int,
        external_tx_id: str,
        transaction_id: str
):
    config_name = str(uuid.uuid4())
    file_content, status_code = await create_new_conf({
        "user_id": int(user_id),
        "config_name": config_name,
        "months": int(months)
    })

    if status_code == 200:
        await update_transaction_status(
            data={
                "transaction_id": int(transaction_id),
                "status": "success",
                "external_tx_id": external_tx_id,
                "comment": f"Оплата за конфигурацию {config_name}"
            }
        )
        file_name = f"{user_id}.conf"
        with open(file_name, "wb") as f:
            f.write(file_content)
        caption = (
                "✅ <b>Оплата прошла успешно!</b>\n\n"
                "Ваша новая конфигурация готова к использованию:"
            )
        await bot.send_document(
            int(user_id),
            FSInputFile(file_name),
            caption=caption,
            parse_mode="HTML"
        )
        os.remove(file_name)