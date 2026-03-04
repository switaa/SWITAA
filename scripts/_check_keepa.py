import sys
import asyncio
import httpx
sys.path.insert(0, "/app")
from app.core.config import get_settings

s = get_settings()
key = s.KEEPA_API_KEY

if not key:
    print("KEEPA_API_KEY: NOT SET")
    sys.exit(1)

print("KEEPA_API_KEY:", key[:8] + "..." + key[-4:])
print("Key length:", len(key))

async def check():
    async with httpx.AsyncClient(timeout=15) as client:
        # Check token status
        resp = await client.get("https://api.keepa.com/token", params={"key": key})
        print("Token endpoint status:", resp.status_code)
        print("Token response:", resp.text[:500])

asyncio.run(check())
