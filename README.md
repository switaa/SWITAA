# Marcus SaaS

Product research and marketplace management platform.

## Stack

- **Backend**: FastAPI + SQLAlchemy + PostgreSQL + Playwright
- **Frontend**: Next.js + Tailwind CSS
- **Automation**: n8n
- **Infra**: Docker Compose + Nginx + Hetzner Cloud

## Quick Start

```bash
cd infra
cp .env.example .env  # Edit with your credentials
docker compose up -d
docker compose exec backend alembic upgrade head
```

## Architecture

```
backend/    - FastAPI API + services (Keepa, SP-API, Helium 10, scoring)
frontend/   - Next.js web app
infra/      - Docker Compose + Nginx configs
n8n/        - Automation workflows
```

## Domains

- `marcus.w3lg.fr` - Application
- `n8n.w3lg.fr` - Workflow automation
