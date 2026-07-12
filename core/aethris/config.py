from pydantic_settings import BaseSettings, SettingsConfigDict


class AethrisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file="/opt/ki-enterprise/core.env", extra="ignore")

    AI_GATEWAY_URL: str = "http://localhost:5002"
    MEMORY_API_URL: str = "http://localhost:5001"
    CEO_API_URL: str = "http://localhost:5000"
    PROJECTS_API_URL: str = "http://localhost:5006"
    INTERNAL_API_KEY: str  # zorunlu, core.env'den gelir
    PROJECTS: list[str]


settings = AethrisSettings()
