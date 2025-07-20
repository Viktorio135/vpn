import os
import httpx
import logging


from dotenv import load_dotenv


from utils.register import register


load_dotenv('/Users/viktorshpakovskij/Step/vpn/.env')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


API_BASE_URL = os.environ.get('API_BASE_URL')


def get_server_jwt_token():
    load_dotenv('/Users/viktorshpakovskij/Step/vpn/.env', override=True)
    return os.environ.get('SERVER_JWT_TOKEN')


async def api_request(method: str, endpoint: str, data: dict = None):
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        try:
            SERVER_JWT_TOKEN = get_server_jwt_token()
            response = await client.request(
                method,
                endpoint,
                headers={
                    "authorization": f"Bearer {SERVER_JWT_TOKEN}"
                },
                json=data
            )
            response.raise_for_status()
            return response.json(), response.status_code
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                error_detail = e.response.json()
                detail = error_detail.get('detail', '')
                if 'expired' in detail:
                    logger.info("Token expired! Getting new token...")
                    if register():
                        SERVER_JWT_TOKEN = get_server_jwt_token()
                        retry_response = await client.request(
                            method,
                            endpoint,
                            headers={
                                "authorization": f"Bearer {SERVER_JWT_TOKEN}"
                            },
                            json=data
                        )
                        retry_response.raise_for_status()
                        return retry_response.json(), retry_response.status_code
                elif 'invalid' in detail:
                    logger.error('token is invalid')
            return None, e.response.status_code
        except Exception as e:
            logging.error(f"API request error: {e}")
            return None, 500


async def create_new_conf(data: dict):
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        try:
            SERVER_JWT_TOKEN = get_server_jwt_token()
            response = await client.request(
                "POST", "/server/get_available_server/",
                headers={
                    "authorization": f"Bearer {SERVER_JWT_TOKEN}"
                },
                json=data
            )
            response.raise_for_status()
            return response.content, response.status_code
        except httpx.HTTPStatusError as e:
            return None, e.response.status_code
        except Exception as e:
            logging.error(f"Error creating new config: {e}")
            return None, 500


async def get_conf_data(config_id: int):
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        try:
            SERVER_JWT_TOKEN = get_server_jwt_token()
            response = await client.request(
                "POST", f"/config/{config_id}/",
                headers={
                    "authorization": f"Bearer {SERVER_JWT_TOKEN}"
                },
            )
            response.raise_for_status()
            return response, 200
        except httpx.HTTPStatusError as e:
            return None, e.response.status_code


async def create_transaction(data: dict):
    return await api_request("POST", "/transaction/create/", data)


async def update_transaction_status(data: dict):
    return await api_request("POST", "/transaction/update_status/", data)


async def renew_conf(config_id: int, months: int):
    return await api_request(
        "POST", f"/config/{config_id}/renew/", {"months": months}
    )


async def reinstall_conf(config_id: int):
    return await api_request("GET", f"/config/{config_id}/reinstall/")
