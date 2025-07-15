import os
import requests

from dotenv import load_dotenv

from utils.env_manager import update_env_var

load_dotenv('/Users/viktorshpakovskij/Step/vpn/.env')


API_BASE_URL = os.environ.get('API_BASE_URL')
REG_TOKEN = os.environ.get('REG_TOKEN')


def register():
    server_data = {
        "server_id": 11111,
        "ip": 'bot',
        'name': 'bot',
        "country": 'bot',
        "max_count_users": 11111,
    }

    response = requests.post(
        f'{API_BASE_URL}auth/register/',
        headers={
            "authorization": f"Bearer {REG_TOKEN}"
        },
        json=server_data,
        timeout=10
    )

    if response.status_code == 200:
        data = response.json()
        token = data.get("token")
        if token:
            update_env_var(
                key='SERVER_JWT_TOKEN',
                value=token
            )
            return True
    return False
