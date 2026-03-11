import httpx
import time

login = httpx.post("http://localhost:8000/api/v1/auth/login", json={
    "email": "contact@switaa.com",
    "password": "Marcus2024!",
})
print(f"Login: {login.status_code}")
if login.status_code != 200:
    print(login.text[:200])
    exit(1)

token = login.json()["access_token"]

t0 = time.time()
r = httpx.get(
    "http://localhost:8000/api/v1/products/top",
    params={
        "min_score": "40",
        "max_bsr": "100000",
        "target_margin": "35",
        "exclude_amazon_seller": "true",
        "limit": "5",
    },
    headers={"Authorization": f"Bearer {token}"},
    timeout=60,
)
print(f"Top status: {r.status_code} ({time.time()-t0:.1f}s)")
print(f"Content-Length: {len(r.text)}")
try:
    data = r.json()
    print(f"Items: {len(data)}")
    if data:
        print(f"First: {data[0]}")
except Exception as e:
    print(f"Parse error: {e}")
    print(f"Response: {r.text[:500]}")
