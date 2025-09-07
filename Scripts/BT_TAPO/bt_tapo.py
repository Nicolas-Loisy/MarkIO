from tapo import ApiClient
import asyncio
import os
from dotenv import load_dotenv

async def main():
    load_dotenv()
    email = os.getenv("TAPO_EMAIL")
    password = os.getenv("TAPO_PASSWORD")
    ip = os.getenv("TAPO_IP")
    client = ApiClient(email, password)
    device = await client.p110(ip)
    await device.on()
    # await device.off()
    # Puis d'autres commandes comme off(), set_brightness(), set_color() selon ton appareil

asyncio.run(main())
