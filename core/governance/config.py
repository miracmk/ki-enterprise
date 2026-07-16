from pydantic_settings import BaseSettings, SettingsConfigDict


class GovernanceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file="/opt/ki-enterprise/core.env", extra="ignore")

    MEMORY_API_URL: str = "http://localhost:5001"
    INTERNAL_API_KEY: str  # zorunlu, core.env'den gelir

    # Uyum skorkarti (Faz D3) canli servislerin /health uclarini okur.
    CEO_API_URL: str = "http://localhost:5000"
    AI_GATEWAY_API_URL: str = "http://localhost:5002"
    EXECUTIVES_API_URL: str = "http://localhost:5003"
    WORKERS_API_URL: str = "http://localhost:5005"
    IMPROVEMENT_API_URL: str = "http://localhost:5010"
    SCHEDULER_API_URL: str = "http://localhost:5013"


settings = GovernanceSettings()
