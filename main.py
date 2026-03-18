import asyncio
import logging

from httpx import AsyncClient

from app.core.config import settings
from app.parsers.avito import AvitoVacanciesParser
from app.proxy.client import SharedHttpClient
from app.proxy.manager import ProxyController
from app.proxy.models import ProxyConfig, ProxyCredentials
from app.proxy.provider import MobileProxyProvider

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, "
        "like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image"
        "/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Sec-Ch-Ua": (
        'Not:A-Brand";v="99", "Google Chrome";v="120", "Chromium";v="120'
    ),
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


async def main() -> None:
    proxy_controller = None
    proxy: str | None = None

    if settings.PROXY_URL:
        credentials = None
        if settings.PROXY_LOGIN and settings.PROXY_PASSWORD:
            credentials = ProxyCredentials(
                username=settings.PROXY_LOGIN,
                password=settings.PROXY_PASSWORD,
            )

        proxy_config = ProxyConfig(
            url=settings.PROXY_URL,
            credentials=credentials,
            rotate_url=settings.PROXY_ROTATE_URL,
            cooldown_seconds=settings.PROXY_COOLDOWN_SECONDS,
        )
        proxy_controller = ProxyController(
            provider=MobileProxyProvider(proxy_config),
            cooldown_seconds=proxy_config.cooldown_seconds,
        )
        proxy = proxy_controller.proxy_url

    async with AsyncClient(
        http2=False, proxy=proxy, headers=HEADERS, timeout=30
    ) as raw_client:
        shared_client = SharedHttpClient(
            raw_client,
            proxy_controller=proxy_controller,
        )
        parser = AvitoVacanciesParser(
            shared_client,
            proxy_controller=proxy_controller,
            run_interval_seconds=settings.PARSER_RUN_INTERVAL_SECONDS,
        )
        await parser.run()


if __name__ == "__main__":
    asyncio.run(main())
