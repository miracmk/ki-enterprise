from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file="/opt/ki-enterprise/core.env", extra="ignore")

    LITELLM_API_BASE: str = "http://localhost:4000/v1"
    LITELLM_API_KEY: str  # zorunlu, core.env'den gelir
    INTERNAL_API_KEY: str  # zorunlu, core.env'den gelir
    # "ki-cloud": LiteLLM'de tanimli, ucretsiz+guclu bulut modelleriyle baslayip
    # otomatik fallback zinciriyle (Groq -> Groq -> Ollama Cloud -> Groq) devam
    # eden bir alias - bkz. infrastructure/litellm/config.yaml. Yerel Ollama
    # KULLANILMAZ (host RAM'i kisitli, kesinti yaratirdi).
    DEFAULT_CHAT_MODEL: str = "ki-cloud"
    DEFAULT_REASON_MODEL: str = "ki-cloud"
    DEFAULT_EMBEDDING_MODEL: str = "mistral-embed"
    DEFAULT_AGENT_MODEL: str = "ki-cloud"

    # Faz C - kota-farkinda ekonomi ("Free as possible"). Redis, core/memory
    # ile AYNI instance/port - ayri bir DB index (bkz. main.py) kullanilarak
    # anahtar cakismasi onlenir.
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 16379
    REDIS_DB: int = 1
    # Gunluk toplam token kotasi (tum modeller toplami) - asilirsa sadece
    # priority="high" istekler gecer. Groq ucretsiz katmanin kaba tahmini
    # gunluk kapasitesine gore VARSAYILAN, gercek deger core.env'den ezilebilir.
    DAILY_TOKEN_BUDGET: int = 1_000_000
    QUOTA_SOFT_THRESHOLD_RATIO: float = 0.8
    CHEAP_FALLBACK_MODEL: str = "ki-cloud-worker"


settings = GatewaySettings()
