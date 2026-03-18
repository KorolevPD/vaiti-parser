from asyncio import sleep
from random import uniform
from typing import Any, Dict, Optional

from httpx import AsyncClient, Response

from app.proxy.manager import ProxyManager


class BaseParser:
    def __init__(
        self,
        http_client: AsyncClient,
        proxy_manager: Optional[ProxyManager] = None,
    ) -> None:
        self.http_client = http_client
        self.proxy_manager = proxy_manager

    async def parse(self) -> None:
        raise NotImplementedError

    async def fetch(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        wait: Optional[float] = None,
    ) -> Response:
        if wait is None:
            wait = uniform(120, 144)

        await sleep(wait)
        r = await self.http_client.get(url, params=params)
        if r.status_code in (302, 429, 403):
            if self.proxy_manager:
                await self.proxy_manager.refresh_proxy()

        r.raise_for_status()
        return r

    async def on_error(self, e: Exception) -> None:
        if self.proxy_manager:
            await self.proxy_manager.refresh_proxy()

    async def run(self) -> None:
        while True:
            if self.proxy_manager:
                await self.proxy_manager.wait_if_paused()

            try:
                await self.parse()
            except Exception as e:
                await self.on_error(e)
