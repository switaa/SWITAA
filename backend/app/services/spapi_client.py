"""Amazon Selling Partner API client with full LWA + STS AssumeRole + SigV4 auth."""
from __future__ import annotations

import logging
import time
from typing import Any

import boto3
import httpx
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials

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
        self.seller_id = settings.SPAPI_SELLER_ID
        self.role_arn = settings.SPAPI_ROLE_ARN
        self.region = settings.SPAPI_REGION
        self.aws_access_key = settings.SPAPI_AWS_ACCESS_KEY_ID
        self.aws_secret_key = settings.SPAPI_AWS_SECRET_ACCESS_KEY

        self._access_token: str | None = None
        self._access_token_expires: float = 0
        self._sts_credentials: dict | None = None
        self._sts_expires: float = 0

    async def _get_access_token(self) -> str:
        """Step 1: LWA token exchange."""
        if self._access_token and time.time() < self._access_token_expires - 300:
            return self._access_token

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(LWA_TOKEN_URL, data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            })
            if resp.status_code != 200:
                logger.error("LWA token error %d: %s", resp.status_code, resp.text[:300])
                resp.raise_for_status()

            data = resp.json()
            self._access_token = data["access_token"]
            self._access_token_expires = time.time() + data.get("expires_in", 3600)
            return self._access_token

    def _get_sts_credentials(self) -> dict:
        """Step 2: STS AssumeRole to get temporary AWS credentials."""
        if self._sts_credentials and time.time() < self._sts_expires - 300:
            return self._sts_credentials

        sts = boto3.client(
            "sts",
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key,
            region_name=self.region,
        )
        response = sts.assume_role(
            RoleArn=self.role_arn,
            RoleSessionName="marcus-spapi-session",
            DurationSeconds=3600,
        )
        creds = response["Credentials"]
        self._sts_credentials = {
            "access_key": creds["AccessKeyId"],
            "secret_key": creds["SecretAccessKey"],
            "session_token": creds["SessionToken"],
        }
        self._sts_expires = time.time() + 3300
        return self._sts_credentials

    def _sign_request(self, method: str, url: str, headers: dict, body: str | None = None) -> dict:
        """Step 3: SigV4 sign the request."""
        sts_creds = self._get_sts_credentials()

        aws_request = AWSRequest(
            method=method,
            url=url,
            headers=headers,
            data=body or "",
        )

        credentials = Credentials(
            access_key=sts_creds["access_key"],
            secret_key=sts_creds["secret_key"],
            token=sts_creds["session_token"],
        )
        SigV4Auth(credentials, "execute-api", self.region).add_auth(aws_request)

        return dict(aws_request.headers)

    async def _request(self, method: str, path: str, params: dict | None = None,
                       json_body: dict | None = None) -> httpx.Response:
        """Execute a fully authenticated SP-API request."""
        access_token = await self._get_access_token()

        if params:
            query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            url = f"{SPAPI_BASE}{path}?{query}"
        else:
            url = f"{SPAPI_BASE}{path}"

        headers = {
            "x-amz-access-token": access_token,
            "Content-Type": "application/json",
            "host": "sellingpartnerapi-eu.amazon.com",
        }

        import json
        body = json.dumps(json_body) if json_body else None
        signed_headers = self._sign_request(method, url, headers, body)

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(
                method=method,
                url=url,
                headers=signed_headers,
                content=body,
            )
            return resp

    async def get_catalog_item(self, asin: str) -> dict[str, Any] | None:
        resp = await self._request("GET", f"/catalog/2022-04-01/items/{asin}", params={
            "marketplaceIds": self.marketplace_id,
            "includedData": "summaries,images,salesRanks",
        })
        if resp.status_code != 200:
            logger.error("SP-API catalog error %d: %s", resp.status_code, resp.text[:200])
            return None
        return resp.json()

    async def get_pricing(self, asin: str) -> dict[str, Any] | None:
        resp = await self._request("GET", "/products/pricing/v0/price", params={
            "MarketplaceId": self.marketplace_id,
            "Asins": asin,
            "ItemType": "Asin",
        })
        if resp.status_code != 200:
            logger.error("SP-API pricing error: %d", resp.status_code)
            return None
        return resp.json()

    async def get_competitive_pricing(self, asin: str) -> dict[str, Any] | None:
        resp = await self._request("GET", "/products/pricing/v0/competitivePrice", params={
            "MarketplaceId": self.marketplace_id,
            "Asins": asin,
            "ItemType": "Asin",
        })
        if resp.status_code != 200:
            logger.debug("SP-API competitive pricing error %d for %s", resp.status_code, asin)
            return None
        return resp.json()

    async def get_fees_estimate(self, asin: str, price: float) -> dict[str, Any] | None:
        """Get FBA/FBM fee estimates for a product."""
        resp = await self._request(
            "POST",
            f"/products/fees/v0/items/{asin}/feesEstimate",
            json_body={
                "FeesEstimateRequest": {
                    "MarketplaceId": self.marketplace_id,
                    "IsAmazonFulfilled": True,
                    "PriceToEstimateFees": {
                        "ListingPrice": {"CurrencyCode": "EUR", "Amount": price},
                    },
                    "Identifier": asin,
                },
            },
        )
        if resp.status_code != 200:
            logger.debug("SP-API fees error %d for %s", resp.status_code, asin)
            return None
        return resp.json()

    async def get_item_offers(self, asin: str) -> dict[str, Any] | None:
        """Get all offers for an ASIN (BuyBox winner, seller list)."""
        resp = await self._request("GET", f"/products/pricing/v0/items/{asin}/offers", params={
            "MarketplaceId": self.marketplace_id,
            "ItemCondition": "New",
        })
        if resp.status_code != 200:
            logger.debug("SP-API offers error %d for %s", resp.status_code, asin)
            return None
        return resp.json()

    async def create_listing(self, sku: str, product_data: dict[str, Any]) -> dict[str, Any] | None:
        resp = await self._request(
            "PUT",
            f"/listings/2021-08-01/items/{self.seller_id}/{sku}",
            params={"marketplaceIds": self.marketplace_id},
            json_body={
                "productType": product_data.get("productType", "PRODUCT"),
                "requirements": "LISTING",
                "attributes": product_data.get("attributes", {}),
            },
        )
        if resp.status_code not in (200, 202):
            logger.error("SP-API listing error: %d: %s", resp.status_code, resp.text[:300])
            return None
        return resp.json()
