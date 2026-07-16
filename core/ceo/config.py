from pydantic_settings import BaseSettings, SettingsConfigDict


class CEOSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file="/opt/ki-enterprise/core.env", extra="ignore")

    PROJECT_NAME: str = "KI_Enterprise_CEO"
    NATS_URL: str = "nats://localhost:14222"
    INTERNAL_API_KEY: str  # zorunlu, core.env'den gelir - servisler-arasi auth

    # CEO'nun araclari (bkz. Build Order Phase 2): Temporal, NATS, Memory, LiteLLM
    TEMPORAL_HOST: str = "localhost:17233"
    TEMPORAL_NAMESPACE: str = "default"
    TASK_QUEUE: str = "ki-enterprise-queue"
    MEMORY_API_URL: str = "http://localhost:5001"
    IMPROVEMENT_API_URL: str = "http://localhost:5010"
    GOVERNANCE_API_URL: str = "http://localhost:5014"
    EXECUTIVES_API_URL: str = "http://localhost:5003"

    REPORT_CONSUMER_DURABLE: str = "ceo-report-collector"
    # Bir dispatch'in "yayinlandi" ile "yapildi" arasindaki mutabakati icin -
    # bu sureden uzun suredir kapanmamis isler SLA ihlali olarak escalate edilir.
    DISPATCH_SLA_SECONDS: int = 1800
    SLA_WATCHDOG_INTERVAL_SECONDS: int = 300
    # Tek dogruluk kaynagi core.env'de - core/projects ile paylasilir.
    PROJECTS: list[str]

    # CEO'nun kullaniciyla dogal dilde konustugu kimlik (bkz. /api/v1/ceo/chat).
    # Dispatch/approve/status uclarini ETKILEMEZ - onlar hala yapisal/programatik.
    CEO_NAME: str = "John"
    AI_GATEWAY_URL: str = "http://localhost:5002"

    # Tek dogruluk kaynagi core.env'de (bkz. yorum orada) - core/departments,
    # core/workflow, core/dashboard ile paylasilir.
    WORKFLOW_TO_DEPARTMENT: dict[str, str]

    # Gercek Ki Ecosystem dizini (apps/ + websites/, klasor bazinda) - PROJECTS
    # (core.env, formal butce/roadmap takibi yapilan projeler) ile AYRI bir
    # katman: buradaki her klasor, core.env'e HIC DOKUNMADAN dogrudan
    # dispatch edilebilir bir proje sayilir (bkz. _ecosystem_project_names).
    ECOSYSTEM_ROOT: str = "/opt/ki-ecosystem"


settings = CEOSettings()
