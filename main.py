import asyncio
import logging
import sys

from curl_cffi.requests import AsyncSession
from mobileproxy import Client

from app.core.config import settings
from app.parsers import BaseParser
from app.parsers.avito import AvitoVacanciesParser
from app.parsers.dreamjob import DreamjobRatingParser
from app.parsers.habr import HabrSalaryParser, HarbRatingParser
from app.proxy.client import SharedHttpClient
from app.proxy.manager import ProxyController
from app.proxy.models import ProxyConfig
from app.proxy.provider import MobileProxyProvider

DAY = 86400
WEEK = DAY * 7
MONTH = DAY * 30


async def main() -> None:
    setup_logging()
    proxy_controller = None
    proxy: str | None = None

    with Client(settings.PROXY_API_KEY) as client:
        proxies = client.get_my_proxy()

    if proxies:
        login = proxies[0].get("proxy_login", "")
        password = proxies[0].get("proxy_pass", "")
        hostname = proxies[0].get("proxy_independent_http_hostname")
        port = proxies[0].get("proxy_independent_port")
        proxy_config = ProxyConfig(
            url=f"http://{login}:{password}@{hostname}:{port}",
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
        timeout=60,
        max_clients=1,
    ) as raw_client:
        shared_client = SharedHttpClient(
            raw_client,
            proxy_controller=proxy_controller,
        )

        parsers: list[BaseParser] = [
            AvitoVacanciesParser(
                http_client=shared_client,
                proxy_controller=proxy_controller,
                run_interval_seconds=DAY,
                request_delay_range=(2.0, 5.0),
            ),
            DreamjobRatingParser(
                http_client=shared_client,
                proxy_controller=proxy_controller,
                run_interval_seconds=WEEK,
            ),
            HarbRatingParser(
                http_client=shared_client,
                proxy_controller=proxy_controller,
                run_interval_seconds=WEEK,
            ),
            HabrSalaryParser(
                http_client=shared_client,
                proxy_controller=proxy_controller,
                run_interval_seconds=MONTH,
            ),
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
