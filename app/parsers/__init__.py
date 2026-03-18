from typing import Optional

from httpx import AsyncClient

from app.proxy.manager import ProxyManager


class BaseParser:
    def __init__(
        self,
        http_client: AsyncClient,
        proxy_manager: Optional[ProxyManager] = None,
    ) -> None:
        self.http = http_client
        self.proxy_manager = proxy_manager

    async def parse(self) -> None:
        raise NotImplementedError

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
