import os
from pydantic_settings import BaseSettings


class EventsSettings(BaseSettings):
    NATS_URL: str = os.getenv("NATS_URL", "nats://localhost:14222")


settings = EventsSettings()
