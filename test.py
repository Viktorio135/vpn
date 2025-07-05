import httpx
import asyncio

from tronpy import Tron
from tronpy.providers import HTTPProvider


TRONGRID_API_KEY='2fe0e177-e3d8-46ec-84c1-060cb4f35d63'
TRON_PROVIDER = HTTPProvider(api_key=TRONGRID_API_KEY)
TRON_NETWORK = "nile"
USDT_CONTRACT_ADDRESS = "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"
DEPOSIT_ADDRESS = 'TYhTGjSJhiUcnTE4hCWckNt6Bb6YDHgndi'


async def check_tron_transaction(sender: str, amount: float) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            # 1. Конвертируем адреса в hex-формат
            to_address = DEPOSIT_ADDRESS
            from_address = sender
            
            # 2. Запрашиваем последние транзакции через TronGrid API
            response = await client.get(
                "https://nile.trongrid.io/v1/accounts/" + to_address + "/transactions/trc20",
                params={
                    "limit": 50,
                    "contract_address": USDT_CONTRACT_ADDRESS,
                    "only_confirmed": "true",
                    "order_by": "block_timestamp,desc"
                },
                headers={"TRON-PRO-API-KEY": TRONGRID_API_KEY}
            )
            print(response.json())
            # 3. Парсим результаты
            transactions = response.json().get('data', [])
            for tx in transactions:
                if (tx['from'] == from_address
                    and tx['to'] == to_address
                    and float(tx['value']) / 1_000_000 >= amount - 0.1  # Учитываем возможные округления
                ):
                    print('zzz')
                    return {
                        'status': 'success',
                        'tx_hash': tx['transaction_id'],
                        'amount': float(tx['value']) / 1_000_000
                    }
            
            return {'status': 'not_found'}
    
    except Exception as e:
        print(f"TRON API error: {e}")
        return {'status': 'error', 'message': str(e)}
    
def main():
    asyncio.run(check_tron_transaction('TRg5PL8vfeGG6p5oZVZx7ZzmghBFdXWm13', 2.5))

if __name__ == '__main__':
    main()