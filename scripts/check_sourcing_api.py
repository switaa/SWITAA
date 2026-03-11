"""Verify sourcing API endpoints are registered."""
import json
import urllib.request

resp = urllib.request.urlopen("http://localhost:8000/openapi.json")
data = json.loads(resp.read())
sourcing_paths = [p for p in data["paths"] if "sourcing" in p]
print("Sourcing endpoints:")
for p in sourcing_paths:
    methods = list(data["paths"][p].keys())
    print(f"  {', '.join(m.upper() for m in methods)} {p}")
print(f"\nTotal: {len(sourcing_paths)} endpoints")
