from pydantic_settings import BaseSettings, SettingsConfigDict


class DepartmentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file="/opt/ki-enterprise/core.env", extra="ignore")

    NATS_URL: str = "nats://localhost:14222"
    MEMORY_API_URL: str = "http://localhost:5001"
    INTERNAL_API_KEY: str  # zorunlu, core.env'den gelir
    TASK_CONSUMER_DURABLE: str = "department-manager"
    # Tek dogruluk kaynagi core.env'de (bkz. yorum orada) - core/workers,
    # core/projects, core/ceo ile paylasilir.
    WORKFLOW_TO_DEPARTMENT: dict[str, str]


settings = DepartmentSettings()
