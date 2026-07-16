from pydantic_settings import BaseSettings, SettingsConfigDict


class ComposioSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file="/opt/ki-enterprise/core.env", extra="ignore")

    INTERNAL_API_KEY: str  # zorunlu, core.env'den gelir
    COMPOSIO_API_KEY: str  # zorunlu, core.env'den gelir

    COMPOSIO_BASE_URL: str = "https://backend.composio.dev"
    # Bagli hesap/toolkit listesinin ne siklikla yeniden cekilecegi
    SYNC_INTERVAL_SECONDS: int = 3600


settings = ComposioSettings()
