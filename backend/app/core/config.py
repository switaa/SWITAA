from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_ENV: str = "dev"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "change-me-in-production"

    DATABASE_URL: str = "postgresql://marcus:marcus_dev@db:5432/marcus"

    JWT_SECRET: str = "change-me-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    CORS_ORIGINS: list[str] = ["http://localhost:3000", "https://marcus.w3lg.fr"]

    KEEPA_API_KEY: str = ""
    SPAPI_LWA_CLIENT_ID: str = ""
    SPAPI_LWA_CLIENT_SECRET: str = ""
    SPAPI_LWA_REFRESH_TOKEN: str = ""
    SPAPI_ROLE_ARN: str = ""
    SPAPI_SELLER_ID: str = ""
    SPAPI_REGION: str = "eu-west-1"
    SPAPI_MARKETPLACE_ID_FR: str = "A13V1IB3VIYZZH"

    APIFY_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4.1"

    HELIUM10_EMAIL: str = ""
    HELIUM10_PASSWORD: str = ""

    @property
    def is_debug(self) -> bool:
        return self.APP_ENV == "dev" or self.DEBUG

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
