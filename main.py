import asyncio
import logging
from random import choice
import sys

from curl_cffi.requests import AsyncSession

from app.core.config import settings
from app.parsers import BaseParser
from app.parsers.avito import AvitoVacanciesParser
from app.parsers.dreamjob import DreamjobRatingParser
from app.parsers.habr import HabrSalaryParser, HarbRatingParser
from app.proxy.client import SharedHttpClient
from app.proxy.manager import ProxyController
from app.proxy.models import ProxyConfig, ProxyCredentials
from app.proxy.provider import MobileProxyProvider


async def main() -> None:
    setup_logging()
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

    ver = choice(["120", "123", "124"])

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit"
            f"/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image"
            "/avif,image/webp,image/apng,*/*;q=0.8"
        ),
        "Accept-Language": choice(
            [
                "ru-RU,ru;q=0.9,en;q=0.8",
                "ru,en;q=0.9",
            ]
        ),
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Sec-Ch-Ua": (
            f'"Google Chrome";v="{ver}", "Chromium";v="{ver}", '
            '"Not_A Brand";v="24"'
        ),
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }

    async with AsyncSession(
        headers=headers,
        proxy=proxy,
        impersonate=f"chrome{ver}",  # type: ignore
        allow_redirects=True,
        http_version="v1",
        timeout=30,
        max_clients=1,
    ) as raw_client:
        shared_client = SharedHttpClient(
            raw_client,
            proxy_controller=proxy_controller,
        )

        parsers: list[BaseParser] = [
            AvitoVacanciesParser(
                shared_client,
                proxy_controller,
                86400,
                request_delay_range=(25.0, 30.0),
            ),
            DreamjobRatingParser(shared_client, proxy_controller, 86400),
            HabrSalaryParser(shared_client, proxy_controller, 86400),
            HarbRatingParser(shared_client, proxy_controller, 86400),
        ]

        tasks = [asyncio.create_task(p.run()) for p in parsers]

        await asyncio.gather(*tasks)


class Formatter(logging.Formatter):
    LEVEL_PREFIX = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO",
        logging.WARNING: "WARNING",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "CRITICAL",
    }

    def format(self, record: logging.LogRecord) -> str:
        levelprefix = self.LEVEL_PREFIX.get(record.levelno, "LVL").ljust(8)
        timestamp = self.formatTime(record, "%d.%m.%Y %H:%M:%S")
        message = record.getMessage()
        return f"{timestamp} | {levelprefix}{message}"


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(Formatter())
    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler],
    )


if __name__ == "__main__":
    asyncio.run(main())
