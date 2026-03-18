import asyncio

from httpx import URL, Proxy


class ProxyManager:
    def __init__(self, url: URL | str, auth: tuple[str, str] | None) -> None:
        self._proxy = Proxy(url, auth=auth)
        self._lock = asyncio.Lock()
        self._pause_event = asyncio.Event()
        self._pause_event.set()

    async def get_proxy(self) -> Proxy:
        return self._proxy

    async def refresh_proxy(self) -> None:
        async with self._lock:
            if not self._pause_event.is_set():
                return  # уже обновляется

            print("🔄 Refreshing proxy...")
            self._pause_event.clear()

            # имитация запроса к API мобильного прокси
            await asyncio.sleep(120)

            print("✅ Proxy updated:", self._proxy)
            self._pause_event.set()

    async def wait_if_paused(self) -> None:
        await self._pause_event.wait()
