from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkflowSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file="/opt/ki-enterprise/core.env", extra="ignore")

    TEMPORAL_HOST: str = "localhost:17233"
    TEMPORAL_NAMESPACE: str = "default"
    TASK_QUEUE: str = "ki-enterprise-queue"
    AI_GATEWAY_URL: str = "http://localhost:5002"
    MEMORY_API_URL: str = "http://localhost:5001"
    EXECUTIVES_API_URL: str = "http://localhost:5003"
    NATS_URL: str = "nats://localhost:14222"
    INTERNAL_API_KEY: str  # zorunlu, core.env'den gelir
    # Tek dogruluk kaynagi core.env'de (bkz. yorum orada) - core/departments,
    # core/ceo, core/dashboard ile paylasilir.
    WORKFLOW_TO_DEPARTMENT: dict[str, str]


settings = WorkflowSettings()
