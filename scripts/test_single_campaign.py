"""Create and run a single test campaign."""
import httpx
import time

BASE = "http://localhost:8000"

# Login
resp = httpx.post(f"{BASE}/api/v1/auth/login", json={"email": "contact@switaa.com", "password": "no26CG73Lg@"})
token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Create one campaign with just 2 keywords
resp = httpx.post(f"{BASE}/api/v1/campaigns/", json={
    "name": "Test Piscine Filtration",
    "niche": "piscine",
    "sub_niche": "filtration",
    "keywords": ["vanne 6 voies piscine", "crepine filtre piscine"],
    "marketplace": "amazon_fr",
    "target_count": 50
}, headers=headers)
print(f"Create: {resp.status_code} {resp.json()}")
campaign_id = resp.json()["id"]

# Run it
resp = httpx.post(f"{BASE}/api/v1/campaigns/{campaign_id}/run", headers=headers)
print(f"Run: {resp.status_code} {resp.json()}")

# Poll status
for i in range(60):
    time.sleep(5)
    resp = httpx.get(f"{BASE}/api/v1/campaigns/{campaign_id}", headers=headers)
    c = resp.json()
    print(f"[{i*5}s] Status: {c['status']} | Phase: {c['phase']} | Progress: {c['progress_pct']}% | Found: {c['found_count']}")
    if c["status"] in ("completed", "error"):
        if c.get("error_message"):
            print(f"Error: {c['error_message']}")
        break

# Get results
resp = httpx.get(f"{BASE}/api/v1/campaigns/{campaign_id}/results", headers=headers)
results = resp.json()
print(f"\nResults: {len(results)} products")
for r in results[:10]:
    print(f"  {r['asin']} | {r['price']:.2f} EUR | Score: {r.get('score', '-')} | {r['title'][:60]}")
