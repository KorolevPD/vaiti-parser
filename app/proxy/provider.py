from abc import ABC, abstractmethod
import logging
from urllib.parse import quote, urlsplit, urlunsplit

import httpx

from .models import ProxyConfig

logger = logging.getLogger(__name__)


class BaseProxyProvider(ABC):
    @property
    @abstractmethod
    def proxy_url(self) -> str | None:
        raise NotImplementedError

    @abstractmethod
    async def rotate_ip(self, reason: str) -> None:
        raise NotImplementedError


class NullProxyProvider(BaseProxyProvider):
    @property
    def proxy_url(self) -> str | None:
        return None

    async def rotate_ip(self, reason: str) -> None:
        logger.warning(
            "Proxy rotation requested without a configured proxy: %s",
            reason,
        )


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

    async def rotate_ip(self, reason: str) -> None:
        if not self._config.rotate_url:
            logger.warning(
                "Proxy rotation requested but PROXY_ROTATE_URL is not set: %s",
                reason,
            )
            return

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(self._config.rotate_url)
            response.raise_for_status()

        logger.info("Proxy IP rotation completed: %s", reason)
