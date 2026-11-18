import os
from homeassistant_api import AsyncClient
import asyncio
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")

api_token = os.getenv("HA_TOKEN")
api_url = os.getenv("HA_URL")
fan_id = os.getenv("FAN_HA_ID")

async def haevent(domain,service,entity):
    async with AsyncClient(
        api_url,
        api_token,
    ) as client:
        await client.trigger_service(domain, service, entity_id=entity)

asyncio.run(haevent("switch","toggle","switch.plug_2"))

def dysonFan(service):
    asyncio.run(haevent("fan",service,fan_id))