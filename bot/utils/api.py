import os
import httpx
import logging


from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


API_BASE_URL = os.getenv('API_BASE_URL')


async def api_request(method: str, endpoint: str, data: dict = None):
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        try:
            response = await client.request(method, endpoint, json=data)
            response.raise_for_status()
            return response.json(), response.status_code
        except httpx.HTTPStatusError as e:
            return None, e.response.status_code
        except Exception as e:
            logging.error(f"API request error: {e}")
            return None, 500


async def create_new_conf(data: dict):
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        try:
            response = await client.request(
                "POST", "/server/get_available_server/", json=data
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
            response = await client.request("POST", f"/config/{config_id}/")
            response.raise_for_status()
            return response, 200
        except httpx.HTTPStatusError as e:
            return None, e.response.status_code


async def renew_conf(config_id: int, months: int):
    return await api_request(
        "POST", f"/config/{config_id}/renew/", {"months": months}
    )


async def reinstall_conf(config_id: int):
    return await api_request("GET", f"/config/{config_id}/reinstall/")
