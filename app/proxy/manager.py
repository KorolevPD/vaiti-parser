import asyncio
from contextlib import asynccontextmanager
import logging
from typing import AsyncIterator

from .provider import BaseProxyProvider, NullProxyProvider

logger = logging.getLogger(__name__)


class ProxyController:
    def __init__(
        self,
        provider: BaseProxyProvider | None = None,
        cooldown_seconds: float = 120,
    ) -> None:
        self._provider = provider or NullProxyProvider()
        self._cooldown_seconds = cooldown_seconds
        self._condition = asyncio.Condition()
        self._active_requests = 0
        self._rotation_requested = False
        self._rotation_in_progress = False
        self._cooldown_until = 0.0

    @property
    def proxy_url(self) -> str | None:
        return self._provider.proxy_url

    @property
    def has_proxy(self) -> bool:
        return self.proxy_url is not None

    @asynccontextmanager
    async def request_slot(self) -> AsyncIterator[None]:
        await self._acquire_request_slot()
        try:
            yield
        finally:
            await self._release_request_slot()

    async def _acquire_request_slot(self) -> None:
        loop = asyncio.get_running_loop()
        async with self._condition:
            while True:
                now = loop.time()
                cooldown_remaining = self._cooldown_until - now
                blocked = (
                    self._rotation_requested
                    or self._rotation_in_progress
                    or cooldown_remaining > 0
                )
                if not blocked:
                    self._active_requests += 1
                    return

                if cooldown_remaining > 0:
                    try:
                        await asyncio.wait_for(
                            self._condition.wait(),
                            timeout=cooldown_remaining,
                        )
                    except TimeoutError:
                        continue
                else:
                    await self._condition.wait()

    async def _release_request_slot(self) -> None:
        async with self._condition:
            self._active_requests -= 1
            self._condition.notify_all()

    async def rotate_proxy(self) -> None:
        async with self._condition:
            if self._rotation_in_progress:
                logger.info(
                    "Proxy rotation already in progress; skipping duplicate"
                )
                return

            self._rotation_requested = True
            self._condition.notify_all()

            while self._active_requests > 0:
                await self._condition.wait()

            self._rotation_requested = False
            self._rotation_in_progress = True

        logger.warning("Rotating proxy")
        try:
            await self._provider.rotate_ip()
        finally:
            loop = asyncio.get_running_loop()
            async with self._condition:
                self._cooldown_until = loop.time() + self._cooldown_seconds
                self._rotation_in_progress = False
                self._condition.notify_all()

    async def wait_until_ready(self) -> None:
        async with self.request_slot():
            return
