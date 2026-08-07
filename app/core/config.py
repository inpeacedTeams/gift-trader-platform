from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Gift Trader API"
    app_env: str = "development"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:5173"
    database_url: str = "postgresql+asyncpg://gift_trader:gift_trader@localhost:5432/gift_trader"
    jwt_secret: str = "change-me-in-production"
    jwt_ttl_seconds: int = 604800
    telegram_bot_token: str | None = None
    tonapi_base_url: str = "https://tonapi.io"
    tonapi_token: str | None = None
    portals_endpoint: str = "https://portal-market.com/api"
    getgems_collection_addresses: str = ""
    source_timeout_seconds: float = 20.0
    source_retries: int = 2
    source_backoff_seconds: float = 0.5
    market_sync_interval_seconds: int = 300
    market_sync_enabled: bool = True
    portfolio_sync_interval_seconds: int = 300
    portfolio_sync_enabled: bool = True
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    @property
    def getgems_collection_list(self) -> list[str]:
        return [address.strip() for address in self.getgems_collection_addresses.split(",") if address.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()
