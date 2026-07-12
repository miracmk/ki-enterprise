from pydantic_settings import BaseSettings, SettingsConfigDict


class ProjectSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file="/opt/ki-enterprise/core.env", extra="ignore")

    MEMORY_API_URL: str = "http://localhost:5001"
    INTERNAL_API_KEY: str  # zorunlu, core.env'den gelir
    # Tek dogruluk kaynagi core.env'de - core/ceo, core/departments, core/workers
    # ile paylasilir.
    PROJECTS: list[str]
    ACTIVE_DEPARTMENTS: list[str]


settings = ProjectSettings()
