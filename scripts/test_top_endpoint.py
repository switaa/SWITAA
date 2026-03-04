import httpx

login = httpx.post("http://localhost:8000/api/v1/auth/login", json={
    "email": "contact@switaa.com",
    "password": "Marcus2024!",
})
print(f"Login: {login.status_code}")
if login.status_code != 200:
    print(login.text[:200])
    exit(1)

token = login.json()["access_token"]

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
)
print(f"Top status: {r.status_code}")
print(f"Response: {r.text[:2000]}")
