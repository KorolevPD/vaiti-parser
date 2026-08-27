from typing import List, Optional

from pydantic import Field, ValidationError, computed_field
from pydantic_settings import BaseSettings
from sqlalchemy.engine.url import make_url


class Settings(BaseSettings):
    """Глобальные настройки."""

    DEBUG: bool = Field(False)

    DATABASE_URL: str = Field("sqlite:///database.db")
    DATABASE_SCHEMA: str = Field("scraper")

    KAFKA_BOOTSTRAP_SERVERS: Optional[str] = Field(None)
    SCHEMA_REGISTRY_URL: Optional[str] = Field(None)

    PROXY_API_KEY: str = Field(...)
    PROXY_COOLDOWN_SECONDS: float = Field(120)

    BOT_NOTIFICATION_URL: str = Field(
        "http://tg-bot:8080/api/v1/notifications/send"
    )
    BOT_NOTIFICATION_USERS: List[int] = [492487922]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def is_sqlite(self) -> bool:
        return make_url(self.DATABASE_URL).get_backend_name() == "sqlite"

    @computed_field
    def database_schema(self) -> Optional[str]:
        return None if self.is_sqlite else self.DATABASE_SCHEMA


try:
    settings = Settings()  # type: ignore
except ValidationError as e:
    raise SystemExit(f"Ошибка конфигурации:\n{e}")
