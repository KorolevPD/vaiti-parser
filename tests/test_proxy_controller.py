import asyncio

import pytest

from app.proxy.manager import ProxyController
from app.proxy.provider import BaseProxyProvider


class DummyProxyProvider(BaseProxyProvider):
    def __init__(self) -> None:
        self.rotate_calls: list[str] = []
        self.rotation_started = asyncio.Event()
        self.release_rotation = asyncio.Event()

    @property
    def proxy_url(self) -> str | None:
        return "http://proxy.test"

    async def rotate_ip(self, reason: str) -> None:
        self.rotate_calls.append(reason)
        self.rotation_started.set()
        await self.release_rotation.wait()


@pytest.mark.asyncio
async def test_rotation_waits_for_active_requests_and_cooldown() -> None:
    provider = DummyProxyProvider()
    controller = ProxyController(provider=provider, cooldown_seconds=0.05)

    active_request_entered = asyncio.Event()
    allow_request_exit = asyncio.Event()
    second_request_entered = asyncio.Event()

    async def first_request() -> None:
        async with controller.request_slot():
            active_request_entered.set()
            await allow_request_exit.wait()

    async def second_request() -> None:
        async with controller.request_slot():
            second_request_entered.set()

    first_task = asyncio.create_task(first_request())
    await active_request_entered.wait()

    rotate_task = asyncio.create_task(
        controller.rotate_proxy("need fresh ip"),
    )
    await asyncio.sleep(0.01)
    assert not provider.rotation_started.is_set()

    second_task = asyncio.create_task(second_request())
    await asyncio.sleep(0.01)
    assert not second_request_entered.is_set()

    allow_request_exit.set()
    await provider.rotation_started.wait()
    assert provider.rotate_calls == ["need fresh ip"]

    await asyncio.sleep(0.01)
    assert not second_request_entered.is_set()

    provider.release_rotation.set()
    await rotate_task
    await second_task
    await first_task

    assert second_request_entered.is_set()
