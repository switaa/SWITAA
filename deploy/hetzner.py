"""Hetzner Cloud server management for Marcus.

Usage:
    python deploy/hetzner.py create    - Create a new server
    python deploy/hetzner.py status    - Show server status
    python deploy/hetzner.py setup     - Install Marcus on the server
    python deploy/hetzner.py destroy   - Delete the server
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from marcus.config.settings import HCLOUD_API_TOKEN

API_BASE = "https://api.hetzner.cloud/v1"
SERVER_NAME = "marcus-worker"
SERVER_TYPE = "cx22"
IMAGE = "ubuntu-24.04"
LOCATION = "nbg1"

CLOUD_INIT = """#cloud-config
packages:
  - python3
  - python3-pip
  - python3-venv
  - git
  - cron

runcmd:
  - mkdir -p /opt/marcus
  - python3 -m venv /opt/marcus/venv
  - /opt/marcus/venv/bin/pip install playwright python-dotenv pydantic pandas openpyxl aiohttp rich streamlit
  - /opt/marcus/venv/bin/python -m playwright install --with-deps chromium
  - echo "0 */6 * * * cd /opt/marcus && /opt/marcus/venv/bin/python -m marcus.main search --marketplace amazon_fr >> /var/log/marcus.log 2>&1" | crontab -
  - echo "Marcus setup complete" >> /var/log/marcus-setup.log
"""


def _headers() -> dict:
    if not HCLOUD_API_TOKEN:
        print("ERROR: HCLOUD_API_TOKEN non configuré dans .env")
        sys.exit(1)
    return {
        "Authorization": f"Bearer {HCLOUD_API_TOKEN}",
        "Content-Type": "application/json",
    }


def create_server():
    print(f"Création du serveur {SERVER_NAME}...")
    resp = requests.post(
        f"{API_BASE}/servers",
        headers=_headers(),
        json={
            "name": SERVER_NAME,
            "server_type": SERVER_TYPE,
            "image": IMAGE,
            "location": LOCATION,
            "user_data": CLOUD_INIT,
            "labels": {"project": "marcus"},
        },
    )
    data = resp.json()

    if resp.status_code == 201:
        server = data["server"]
        root_pw = data.get("root_password", "N/A")
        print(f"Serveur créé:")
        print(f"  ID:    {server['id']}")
        print(f"  IP:    {server['public_net']['ipv4']['ip']}")
        print(f"  Root:  {root_pw}")
        print(f"  Type:  {SERVER_TYPE}")
        print(f"\nLe serveur s'installe automatiquement (cloud-init).")
        print(f"Connecte-toi avec: ssh root@{server['public_net']['ipv4']['ip']}")
    else:
        print(f"Erreur: {json.dumps(data, indent=2)}")


def server_status():
    resp = requests.get(f"{API_BASE}/servers", headers=_headers(), params={"name": SERVER_NAME})
    data = resp.json()
    servers = data.get("servers", [])

    if not servers:
        print(f"Aucun serveur '{SERVER_NAME}' trouvé.")
        return

    for s in servers:
        print(f"Serveur: {s['name']}")
        print(f"  Status:  {s['status']}")
        print(f"  IP:      {s['public_net']['ipv4']['ip']}")
        print(f"  Type:    {s['server_type']['name']}")
        print(f"  Image:   {s['image']['name']}")
        print(f"  Créé:    {s['created']}")


def destroy_server():
    resp = requests.get(f"{API_BASE}/servers", headers=_headers(), params={"name": SERVER_NAME})
    servers = resp.json().get("servers", [])

    if not servers:
        print(f"Aucun serveur '{SERVER_NAME}' trouvé.")
        return

    server_id = servers[0]["id"]
    confirm = input(f"Supprimer le serveur {SERVER_NAME} (ID: {server_id}) ? [y/N] ")
    if confirm.lower() != "y":
        print("Annulé.")
        return

    resp = requests.delete(f"{API_BASE}/servers/{server_id}", headers=_headers())
    if resp.status_code == 200:
        print(f"Serveur {SERVER_NAME} supprimé.")
    else:
        print(f"Erreur: {resp.json()}")


def setup_server():
    resp = requests.get(f"{API_BASE}/servers", headers=_headers(), params={"name": SERVER_NAME})
    servers = resp.json().get("servers", [])

    if not servers:
        print("Aucun serveur trouvé. Lance `python deploy/hetzner.py create` d'abord.")
        return

    ip = servers[0]["public_net"]["ipv4"]["ip"]
    print(f"Pour déployer Marcus sur {ip}:")
    print(f"  1. scp -r marcus/ root@{ip}:/opt/marcus/")
    print(f"  2. scp .env root@{ip}:/opt/marcus/.env")
    print(f"  3. ssh root@{ip} 'cd /opt/marcus && /opt/marcus/venv/bin/python -m marcus.main search'")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]
    commands = {
        "create": create_server,
        "status": server_status,
        "setup": setup_server,
        "destroy": destroy_server,
    }

    if cmd in commands:
        commands[cmd]()
    else:
        print(f"Commande inconnue: {cmd}")
        print(__doc__)
