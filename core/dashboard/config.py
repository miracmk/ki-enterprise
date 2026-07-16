from pydantic_settings import BaseSettings, SettingsConfigDict


class DashboardSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file="/opt/ki-enterprise/core.env", extra="ignore")

    CEO_API_URL: str = "http://localhost:5000"
    MEMORY_API_URL: str = "http://localhost:5001"
    AI_GATEWAY_URL: str = "http://localhost:5002"
    EXECUTIVES_API_URL: str = "http://localhost:5003"
    DEPARTMENTS_API_URL: str = "http://localhost:5004"
    WORKERS_API_URL: str = "http://localhost:5005"
    PROJECTS_API_URL: str = "http://localhost:5006"
    SKILLS_API_URL: str = "http://localhost:5007"
    FINANCE_API_URL: str = "http://localhost:5011"
    INTERNAL_API_KEY: str  # zorunlu, core.env'den gelir - servisler-arasi (sunucu-sunucu)
    DASHBOARD_UI_TOKEN: str  # zorunlu - SADECE /ui sayfasina gomulur, kapsamlandirilmis
    DASHBOARD_USERNAME: str  # zorunlu - /ui login ekrani
    DASHBOARD_PASSWORD: str  # zorunlu - /ui login ekrani
    PROJECTS: list[str]
    ACTIVE_DEPARTMENTS: list[str]
    DEPARTMENT_TO_CHIEF: dict[str, str]
    WORKFLOW_TO_DEPARTMENT: dict[str, str]
    TWENTY_API_URL: str = "http://localhost:3020/graphql"
    TWENTY_API_KEY: str = ""
    COMPOSIO_API_URL: str = "http://localhost:5012"


settings = DashboardSettings()
