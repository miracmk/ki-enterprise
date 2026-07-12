from pydantic_settings import BaseSettings, SettingsConfigDict


class ImprovementSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file="/opt/ki-enterprise/core.env", extra="ignore")

    MEMORY_API_URL: str = "http://localhost:5001"
    PROJECTS_API_URL: str = "http://localhost:5006"
    SKILLS_API_URL: str = "http://localhost:5007"
    INTERNAL_API_KEY: str  # zorunlu, core.env'den gelir
    PROJECTS: list[str]
    ACTIVE_DEPARTMENTS: list[str]
    WORKFLOW_TO_DEPARTMENT: dict[str, str]


settings = ImprovementSettings()
