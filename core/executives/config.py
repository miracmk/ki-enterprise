from pydantic_settings import BaseSettings, SettingsConfigDict


class ExecutiveSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file="/opt/ki-enterprise/core.env", extra="ignore")

    AI_GATEWAY_URL: str = "http://localhost:5002"
    MEMORY_API_URL: str = "http://localhost:5001"
    GOVERNANCE_API_URL: str = "http://localhost:5014"
    INTERNAL_API_KEY: str  # zorunlu, core.env'den gelir
    # "ki-cloud": ucretsiz+guclu bulut modeli + otomatik fallback zinciri
    # (bkz. infrastructure/litellm/config.yaml). Yerel Ollama kullanilmaz.
    REVIEW_MODEL: str = "ki-cloud"

    # Faz A5, Katman 2 - Chief QC: worker'in "completed_low_quality" isaretledigi
    # ciktilari ilgili Chief'in bakis acisiyla BAGIMSIZ yeniden degerlendirir.
    NATS_URL: str = "nats://localhost:14222"
    QC_CONSUMER_DURABLE: str = "executive-qc"
    QUALITY_MIN_SCORE: int = 60
    MAX_REVISIONS: int = 1
    # Tek dogruluk kaynagi core.env'de - core/dashboard ile paylasilir.
    DEPARTMENT_TO_CHIEF: dict[str, str]


settings = ExecutiveSettings()
