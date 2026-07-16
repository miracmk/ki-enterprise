from pydantic_settings import BaseSettings, SettingsConfigDict


class MemorySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file="/opt/ki-enterprise/core.env", extra="ignore")

    POSTGRES_PASSWORD: str  # zorunlu, core.env'den gelir
    POSTGRES_URL: str = ""  # asagida POSTGRES_PASSWORD ile birlikte kurulur

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 16379
    QDRANT_URL: str = "http://localhost:16333"
    MINIO_ENDPOINT: str = "localhost:19000"
    MINIO_ACCESS_KEY: str = "kiadmin"
    MINIO_SECRET_KEY: str  # zorunlu, core.env'den gelir
    MINIO_BUCKET: str = "ki-memory"
    LITELLM_API_BASE: str = "http://localhost:4000/v1"
    LITELLM_API_KEY: str  # zorunlu, core.env'den gelir
    INTERNAL_API_KEY: str  # zorunlu, core.env'den gelir
    EMBEDDING_MODEL: str = "mistral-embed"
    EMBEDDING_DIM: int = 1024
    SHORT_MEMORY_TTL_SECONDS: int = 3600

    def model_post_init(self, __context) -> None:
        if not self.POSTGRES_URL:
            self.POSTGRES_URL = f"postgresql://ki:{self.POSTGRES_PASSWORD}@localhost:15432/ki_ai"


settings = MemorySettings()
