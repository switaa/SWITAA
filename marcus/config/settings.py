import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

HCLOUD_API_TOKEN = os.getenv("HCLOUD_API_TOKEN", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
HELIUM10_EMAIL = os.getenv("HELIUM10_EMAIL", "")
HELIUM10_PASSWORD = os.getenv("HELIUM10_PASSWORD", "")
KEEPA_EMAIL = os.getenv("KEEPA_EMAIL", "")
KEEPA_PASSWORD = os.getenv("KEEPA_PASSWORD", "")

DB_PATH = BASE_DIR / "marcus" / "data" / "marcus.db"
BROWSER_STATE_DIR = BASE_DIR / "marcus" / "data" / "browser_state"

SCORING_WEIGHTS = {
    "margin": 0.35,
    "competition": 0.25,
    "demand": 0.25,
    "bsr": 0.15,
}

SCORING_THRESHOLDS = {
    "min_margin_pct": 20,
    "max_competition_sellers": 50,
    "min_monthly_sales": 100,
    "max_bsr": 100_000,
}
