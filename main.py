import asyncio
import logging
import sys

from curl_cffi.requests import AsyncSession

from app.core.config import settings
from app.parsers import BaseParser
from app.parsers.avito import AvitoVacanciesParser
from app.parsers.dreamjob import DreamjobRatingParser
from app.parsers.habr import HabrSalaryParser, HarbRatingParser
from app.parsers.vilky import VilkySalaryParser
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

    async with AsyncSession(
        proxy=proxy,
        impersonate="chrome",
        allow_redirects=True,
        http_version="v2",
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
                86400,
                request_delay_range=(2.0, 10.0),
            ),
            DreamjobRatingParser(shared_client, 86400),
            HabrSalaryParser(shared_client, 86400),
            HarbRatingParser(shared_client, 86400),
            VilkySalaryParser(shared_client, 86400),
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
