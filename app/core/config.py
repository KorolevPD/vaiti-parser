from typing import Optional

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Глобальные настройки."""

    DATABASE_URL: str = Field("sqlite:///database.db")
    KAFKA_BOOTSTRAP_SERVERS: Optional[str] = Field(None)

    PROXY_URL: Optional[str] = Field(None)
    PROXY_LOGIN: Optional[str] = Field(None)
    PROXY_PASSWORD: Optional[str] = Field(None)
    PROXY_ROTATE_URL: Optional[str] = Field(None)
    PROXY_COOLDOWN_SECONDS: float = Field(120)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


try:
    settings = Settings()  # type: ignore
except ValidationError as e:
    raise SystemExit(f"Ошибка конфигурации:\n{e}")
