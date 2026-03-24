from abc import ABC, abstractmethod
import asyncio
import logging

from curl_cffi import Response

from app.proxy.client import SharedHttpClient
from app.proxy.manager import ProxyController

logger = logging.getLogger(__name__)


class ProxyRefreshRequired(RuntimeError):
    pass


class BaseParser(ABC):
    parser_name = "base"

    def __init__(
        self,
        http_client: SharedHttpClient,
        proxy_controller: ProxyController | None = None,
        run_interval_seconds: float = 900,
        failure_backoff_seconds: float = 10,
        request_delay_range: tuple[float, float] | None = None,
    ) -> None:
        self.http_client = http_client
        self.proxy_controller = proxy_controller
        self.run_interval_seconds = run_interval_seconds
        self.failure_backoff_seconds = failure_backoff_seconds
        self.request_delay_range = request_delay_range

    @abstractmethod
    async def parse_once(self) -> None:
        raise NotImplementedError

    async def fetch(self, url: str, **kwargs: object) -> Response:
        return await self.http_client.get(
            url,
            delay_range=self.request_delay_range,
            **kwargs,
        )

    async def request_proxy_refresh(self, reason: str) -> None:
        if not self.proxy_controller:
            raise ProxyRefreshRequired(reason)

        await self.proxy_controller.rotate_proxy()

    async def run(self) -> None:
        backoff = self.failure_backoff_seconds
        while True:
            try:
                await self.parse_once()
                backoff = self.failure_backoff_seconds
                await asyncio.sleep(self.run_interval_seconds)
            except ProxyRefreshRequired as e:
                logger.warning(
                    "Refreshing proxy after parser signal from '%s': %s",
                    self.parser_name,
                    e,
                )
                if self.proxy_controller:
                    await self.request_proxy_refresh(str(e))
                else:
                    logger.warning(
                        "Proxy refresh requested by '%s', but proxy is not "
                        "configured",
                        self.parser_name,
                    )
                await asyncio.sleep(backoff)
            except Exception as e:
                logger.exception(
                    "Parser '%s' failed: '%s'",
                    self.parser_name,
                    e,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 300)
