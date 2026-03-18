import asyncio
from typing import List

from httpx import AsyncClient

from app.core.config import settings
from app.parsers import BaseParser
from app.parsers.avito import AvitoVacanciesParser
from app.parsers.dreamjob import DreamjobRatingParser
from app.parsers.habr import HabrSalaryParser, HarbRatingParser
from app.parsers.vilky import VilkySalaryParser
from app.proxy.manager import ProxyManager


async def main() -> None:
    http_client = AsyncClient(http2=False)

    proxy_manager = None
    if settings.PROXY_URL:
        if settings.PROXY_LOGIN and settings.PROXY_PASSWORD:
            auth = (settings.PROXY_LOGIN, settings.PROXY_PASSWORD)
        proxy_manager = ProxyManager(settings.PROXY_URL, auth or None)

    parsers: List[BaseParser] = [
        AvitoVacanciesParser(http_client, proxy_manager),
        DreamjobRatingParser(http_client, proxy_manager),
        HabrSalaryParser(http_client, proxy_manager),
        HarbRatingParser(http_client, proxy_manager),
        VilkySalaryParser(http_client, proxy_manager),
    ]

    tasks = [asyncio.create_task(p.run()) for p in parsers]

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
