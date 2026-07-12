from pydantic_settings import BaseSettings, SettingsConfigDict


class FinanceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file="/opt/ki-enterprise/core.env", extra="ignore")

    MEMORY_API_URL: str = "http://localhost:5001"
    INTERNAL_API_KEY: str  # zorunlu, core.env'den gelir

    # Ucretsiz, anahtarsiz gercek piyasa veri kaynaklari (sirket politikasi:
    # once ucretsiz - bu servis hicbir ucretli piyasa veri API'sine baglanmaz).
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3"
    # Stooq canli testte TUTARSIZ cikti (Cloudflare JS-challenge sayfasi
    # donuyor, User-Agent'tan BAGIMSIZ) - Yahoo Finance'in chart API'sine
    # gecildi (anahtarsiz/ucretsiz, browser User-Agent ile guvenilir calisti).
    YAHOO_FINANCE_URL: str = "https://query1.finance.yahoo.com/v8/finance/chart"
    # exchangerate.host artik ucretsiz erisim icin access_key istiyor (2026
    # itibariyla politika degisti) - open.er-api.com anahtarsiz/ucretsiz
    # alternatifine gecildi (canli testte bulundu).
    EXCHANGERATE_URL: str = "https://open.er-api.com/v6"


settings = FinanceSettings()
