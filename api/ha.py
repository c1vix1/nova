import os
from homeassistant_api import AsyncClient
import asyncio
from dotenv import load_dotenv

# Initialize client (requires your HA URL and a Long-Lived Access Token)
with Client("", "YOUR_LONG_LIVED_ACCESS_TOKEN") as client:
    # Trigger a service, such as toggling a light or switch
    light = client.get_domain("light")
    light.turn_on(entity_id="light.living_room")
