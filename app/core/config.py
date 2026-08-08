from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Verified TON gift collections. Override with GETGEMS_COLLECTION_ADDRESSES.
DEFAULT_GIFT_COLLECTIONS = ",".join(
    [
        # Plush Pepes
        "EQBG-g6ahkAUGWpefWbx-D_9sQ8oWbvy6puuq78U2c4NUDFS",
        # Durov's Caps
        "EQD9ikZq6xPgKjzmdBG0G0S80RvUJjbwgHrPZXDKc_wsE84w",
    ]
)
# Sources that need no credentials. Add "portals" or "fragment" once configured.
DEFAULT_MARKET_SOURCES = "tonnel,getgems"
# Free router: OpenRouter picks an available zero cost model per request.
DEFAULT_AI_MODEL = "openrouter/free"


class Settings(BaseSettings):
    app_name: str = "Gift Trader API"
    app_env: str = "development"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:5173"
    database_url: str = "postgresql+asyncpg://gift_trader:gift_trader@localhost:5432/gift_trader"
    jwt_secret: str = "change-me-in-production"
    jwt_ttl_seconds: int = 604800
    telegram_bot_token: str | None = None
    openrouter_api_key: str | None = None
    openrouter_model: str = DEFAULT_AI_MODEL
    openrouter_site_url: str = "https://github.com/inpeacedTeams/gift-trader-platform"
    ai_timeout_seconds: float = 45.0
    ai_requests_per_hour: int = 30
    ai_verdict_cache_seconds: int = 600
    tonapi_base_url: str = "https://tonapi.io"
    tonapi_token: str | None = None
    tonnel_endpoint: str = "https://gifts2.tonnel.network/api/pageGifts"
    tonnel_history_endpoint: str = "https://gifts2.tonnel.network/api/saleHistory"
    tonnel_auth_data: str | None = None
    portals_endpoint: str = "https://portals-market.com/api/nfts/search"
    portals_auth_data: str | None = None
    getgems_collection_addresses: str = DEFAULT_GIFT_COLLECTIONS
    market_sources: str = DEFAULT_MARKET_SOURCES
    source_timeout_seconds: float = 20.0
    source_retries: int = 2
    source_backoff_seconds: float = 0.5
    market_sync_interval_seconds: int = 300
    market_sync_enabled: bool = True
    trade_sync_interval_seconds: int = 900
    trade_sync_enabled: bool = True
    portfolio_sync_interval_seconds: int = 300
    portfolio_sync_enabled: bool = True
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @staticmethod
    def _split(value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return self._split(self.cors_origins)

    @property
    def getgems_collection_list(self) -> list[str]:
        return self._split(self.getgems_collection_addresses)

    @property
    def market_source_list(self) -> list[str]:
        return [source.lower() for source in self._split(self.market_sources)]


@lru_cache
def get_settings() -> Settings:
    return Settings()
