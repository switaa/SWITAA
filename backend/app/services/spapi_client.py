"""Amazon Selling Partner API client."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger("marcus.spapi")

LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"
SPAPI_BASE = "https://sellingpartnerapi-eu.amazon.com"


class SPAPIClient:
    def __init__(self):
        settings = get_settings()
        self.client_id = settings.SPAPI_LWA_CLIENT_ID
        self.client_secret = settings.SPAPI_LWA_CLIENT_SECRET
        self.refresh_token = settings.SPAPI_LWA_REFRESH_TOKEN
        self.marketplace_id = settings.SPAPI_MARKETPLACE_ID_FR
        self._access_token: str | None = None

    async def _get_access_token(self) -> str:
        if self._access_token:
            return self._access_token

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(LWA_TOKEN_URL, data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            })
            resp.raise_for_status()
            self._access_token = resp.json()["access_token"]
            return self._access_token

    async def _headers(self) -> dict[str, str]:
        token = await self._get_access_token()
        return {
            "x-amz-access-token": token,
            "Content-Type": "application/json",
        }

    async def get_catalog_item(self, asin: str) -> dict[str, Any] | None:
        headers = await self._headers()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{SPAPI_BASE}/catalog/2022-04-01/items/{asin}",
                headers=headers,
                params={
                    "marketplaceIds": self.marketplace_id,
                    "includedData": "summaries,images,salesRanks",
                },
            )
            if resp.status_code != 200:
                logger.error(f"SP-API catalog error {resp.status_code}: {resp.text[:200]}")
                return None
            return resp.json()

    async def get_pricing(self, asin: str) -> dict[str, Any] | None:
        headers = await self._headers()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{SPAPI_BASE}/products/pricing/v0/price",
                headers=headers,
                params={
                    "MarketplaceId": self.marketplace_id,
                    "Asins": asin,
                    "ItemType": "Asin",
                },
            )
            if resp.status_code != 200:
                logger.error(f"SP-API pricing error: {resp.status_code}")
                return None
            return resp.json()

    async def get_competitive_pricing(self, asin: str) -> dict[str, Any] | None:
        headers = await self._headers()
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{SPAPI_BASE}/products/pricing/v0/competitivePrice",
                headers=headers,
                params={
                    "MarketplaceId": self.marketplace_id,
                    "Asins": asin,
                    "ItemType": "Asin",
                },
            )
            if resp.status_code != 200:
                return None
            return resp.json()

    async def create_listing(self, sku: str, product_data: dict[str, Any]) -> dict[str, Any] | None:
        """Push a listing to Amazon via SP-API Listings API."""
        headers = await self._headers()
        seller_id = get_settings().SPAPI_SELLER_ID
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.put(
                f"{SPAPI_BASE}/listings/2021-08-01/items/{seller_id}/{sku}",
                headers=headers,
                params={"marketplaceIds": self.marketplace_id},
                json={
                    "productType": product_data.get("productType", "PRODUCT"),
                    "requirements": "LISTING",
                    "attributes": product_data.get("attributes", {}),
                },
            )
            if resp.status_code not in (200, 202):
                logger.error(f"SP-API listing error: {resp.status_code}: {resp.text[:300]}")
                return None
            return resp.json()
