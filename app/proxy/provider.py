from abc import ABC, abstractmethod
import json
import logging
from urllib.parse import quote, urlsplit, urlunsplit

from curl_cffi import AsyncSession

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
        if not self._config.rotate_url:
            logger.warning(
                "Proxy rotation requested but PROXY_ROTATE_URL is not set"
            )
            return

        async with AsyncSession(timeout=300) as client:
            r = await client.get(self._config.rotate_url)
            r.raise_for_status()

            data = json.loads(r.text)
            if data.get("status", "ERR") == "ERR":
                raise ProxyRotationError(data.get("message"))

        logger.info("Proxy IP rotation completed")
