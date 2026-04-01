from abc import ABC, abstractmethod
import logging
from urllib.parse import quote, urlsplit, urlunsplit

from mobileproxy import Client

from app.core.config import settings

from .models import ProxyConfig

logger = logging.getLogger(__name__)


class ProxyRotationError(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)


class BaseProxyProvider(ABC):
    @property
    @abstractmethod
    def proxy_url(self) -> str | None:
        raise NotImplementedError

    @abstractmethod
    async def rotate_ip(self) -> None:
        raise NotImplementedError


class NullProxyProvider(BaseProxyProvider):
    @property
    def proxy_url(self) -> str | None:
        return None

    async def rotate_ip(self) -> None:
        logger.warning("Proxy rotation requested without a configured proxy")


class MobileProxyProvider(BaseProxyProvider):
    def __init__(self, config: ProxyConfig) -> None:
        self._config = config

    @property
    def proxy_url(self) -> str | None:
        if not self._config.credentials:
            return self._config.url

        parts = urlsplit(self._config.url)
        username = quote(self._config.credentials.username, safe="")
        password = quote(self._config.credentials.password, safe="")
        hostname = parts.hostname or ""
        port = f":{parts.port}" if parts.port else ""
        netloc = f"{username}:{password}@{hostname}{port}"
        return urlunsplit(
            (parts.scheme, netloc, parts.path, parts.query, parts.fragment),
        )

    async def rotate_ip(self) -> None:
        with Client(settings.PROXY_API_KEY) as client:
            r = client.change_equipment(
                proxy_id=client.get_my_proxy()[0].get("proxy_id"),
                country_id=1,
                check_after_change=True,
            )
            if r.get("status", "ERR") == "ERR":
                raise ProxyRotationError(r.get("message"))

        logger.info("Proxy IP rotation completed")
