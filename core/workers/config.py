from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file="/opt/ki-enterprise/core.env", extra="ignore")

    NATS_URL: str = "nats://localhost:14222"
    AI_GATEWAY_URL: str = "http://localhost:5002"
    MEMORY_API_URL: str = "http://localhost:5001"
    INTERNAL_API_KEY: str  # zorunlu, core.env'den gelir
    TASK_CONSUMER_DURABLE: str = "worker-pool"
    # Tek dogruluk kaynagi core.env'de - core/departments, core/projects,
    # core/ceo ile paylasilir.
    WORKFLOW_TO_DEPARTMENT: dict[str, str]


settings = WorkerSettings()
