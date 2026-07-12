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
    DEFAULT_EMBEDDING_MODEL: str = "local-nomic-embed"
    DEFAULT_AGENT_MODEL: str = "ki-cloud"


settings = GatewaySettings()
