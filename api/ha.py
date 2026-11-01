import os
from homeassistant_api import AsyncClient
import asyncio
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")

api_token = os.getenv("HA_TOKEN")
api_url = os.getenv("HA_URL")

async def main():
    async with AsyncClient(
        api_url,
        api_token,
    ) as client:
        await client.trigger_service("light", "turn_on", entity_id="light.living_room")