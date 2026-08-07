from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Gift Trader API"
    app_env: str = "development"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:5173"
    database_url: str = "postgresql+asyncpg://gift_trader:gift_trader@localhost:5432/gift_trader"
    tonapi_base_url: str = "https://tonapi.io"
    tonapi_token: str | None = None
    portals_endpoint: str = "https://portal-market.com/api"
    source_timeout_seconds: float = 20.0
    source_retries: int = 2
    source_backoff_seconds: float = 0.5
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()
