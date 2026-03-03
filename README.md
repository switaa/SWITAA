# Marcus

Outil de recherche de produits Marketplace. Scrape Helium 10 et Keepa, analyse les opportunités et affiche les résultats dans un dashboard.

## Setup

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

Copier `.env.example` vers `.env` et remplir les credentials.

## Utilisation

### Recherche de produits

```bash
python -m marcus.main search --marketplace amazon_fr --min-price 15 --max-price 50
python -m marcus.main search --marketplace amazon_fr --visible  # avec navigateur visible
```

### Export des résultats

```bash
python -m marcus.main export --format csv
python -m marcus.main export --format excel
```

### Dashboard

```bash
python -m marcus.main dashboard
```

## Déploiement Hetzner

```bash
python deploy/hetzner.py create   # Créer un serveur
python deploy/hetzner.py status   # Voir le statut
python deploy/hetzner.py setup    # Instructions de déploiement
python deploy/hetzner.py destroy  # Supprimer le serveur
```
