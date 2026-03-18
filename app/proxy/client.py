import asyncio
import logging
from random import uniform
from typing import Any

import httpx

from app.proxy.manager import ProxyController

logger = logging.getLogger(__name__)

BLOCKING_STATUSES = {302, 403, 407, 429}


class SharedHttpClient:
    def __init__(
        self,
        client: httpx.AsyncClient,
        proxy_controller: ProxyController | None = None,
        min_delay: float = 0.5,
        max_delay: float = 1.5,
        retry_attempts: int = 2,
    ) -> None:
        self._client = client
        self._proxy_controller = proxy_controller
        self._min_delay = min_delay
        self._max_delay = max_delay
        self._retry_attempts = retry_attempts

    async def request(
        self,
        method: str,
        url: str,
        *,
        parser_name: str,
        **kwargs: Any,
    ) -> httpx.Response:
        attempt = 0
        while True:
            attempt += 1
            await asyncio.sleep(uniform(self._min_delay, self._max_delay))

            try:
                if self._proxy_controller:
                    async with self._proxy_controller.request_slot():
                        response = await self._client.request(
                            method,
                            url,
                            **kwargs,
                        )
                else:
                    response = await self._client.request(
                        method,
                        url,
                        **kwargs,
                    )
            except httpx.TransportError as exc:
                if (
                    not self._proxy_controller
                    or attempt > self._retry_attempts
                ):
                    raise

                await self._proxy_controller.rotate_proxy(
                    f"{parser_name}: transport error for {url}: {exc!r}",
                )
                continue

            if response.status_code in BLOCKING_STATUSES:
                if (
                    not self._proxy_controller
                    or attempt > self._retry_attempts
                ):
                    response.raise_for_status()

                await self._proxy_controller.rotate_proxy(
                    f"{parser_name}: status {response.status_code} for {url}",
                )
                continue

            response.raise_for_status()
            return response

    async def get(
        self,
        url: str,
        *,
        parser_name: str,
        **kwargs: Any,
    ) -> httpx.Response:
        return await self.request(
            "GET",
            url,
            parser_name=parser_name,
            **kwargs,
        )
