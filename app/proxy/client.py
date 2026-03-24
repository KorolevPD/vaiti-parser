import asyncio
import logging
from random import uniform
from typing import Any, Literal

from curl_cffi import AsyncSession, Response
from curl_cffi.requests.exceptions import RequestException

from app.proxy.manager import ProxyController

logger = logging.getLogger(__name__)

BLOCKING_STATUSES = {302, 403, 407, 429}


class SharedHttpClient:
    def __init__(
        self,
        client: AsyncSession[Response],
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
        method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"],
        url: str,
        *,
        delay_range: tuple[float, float] | None = None,
        **kwargs: Any,
    ) -> Response:
        attempt = 0
        while True:
            attempt += 1
            min_delay, max_delay = delay_range or (
                self._min_delay,
                self._max_delay,
            )
            await asyncio.sleep(uniform(min_delay, max_delay))

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
            except RequestException as e:
                if (
                    not self._proxy_controller
                    or attempt > self._retry_attempts
                ):
                    raise
                logger.error(f"Failed request: {e}")
                await self._proxy_controller.rotate_proxy()
                continue

            if response.status_code in BLOCKING_STATUSES:
                self._client.cookies.clear()
                if (
                    not self._proxy_controller
                    or attempt > self._retry_attempts
                ):
                    response.raise_for_status()  # type: ignore

                if self._proxy_controller:
                    await self._proxy_controller.rotate_proxy()
                continue

            response.raise_for_status()  # type: ignore
            return response

    async def get(
        self,
        url: str,
        delay_range: tuple[float, float] | None = None,
        **kwargs: Any,
    ) -> Response:
        return await self.request(
            "GET",
            url,
            delay_range=delay_range,
            **kwargs,
        )
