"""Check Keepa API token balance."""
import httpx
import os
import sys

sys.path.insert(0, "/app")

key = os.environ.get("KEEPA_API_KEY", "")
if not key:
    print("KEEPA_API_KEY not set")
    sys.exit(1)

r = httpx.get("https://api.keepa.com/token", params={"key": key})
print(r.json())
