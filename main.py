import asyncio
from datetime import datetime as dt
import logging
from typing import List, Tuple
from zoneinfo import ZoneInfo

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.logging import setup_logging
from app.parsers import BaseParser
from app.parsers.avito import AvitoVacanciesParser
from app.parsers.dreamjob import DreamjobRatingParser
from app.parsers.habr import (
    HabrSalaryParser,
    HabrVacancyParser,
    HarbRatingParser,
)
from app.runtime.state import init_proxy_controller
from app.scheduler.jobs import run_parser

logger = logging.getLogger(__name__)

TIMEZONE = "Europe/Moscow"


async def main() -> None:
    setup_logging()
    init_proxy_controller()

    per_day = CronTrigger(hour=2)
    per_week = CronTrigger(day_of_week="mon", hour=2)
    per_month = CronTrigger(day=1, hour=2)

    parsers: List[Tuple[type[BaseParser], CronTrigger]] = [
        (AvitoVacanciesParser, per_day),
        (HabrVacancyParser, per_day),
        (DreamjobRatingParser, per_week),
        (HarbRatingParser, per_week),
        (HabrSalaryParser, per_month),
    ]

    scheduler = AsyncIOScheduler(
        jobstores={
            "default": SQLAlchemyJobStore(
                url=settings.DATABASE_URL,
                tableschema=settings.database_schema,
            )
        },
        timezone=TIMEZONE,
    )
    scheduler.start()

    for parser, trigger in parsers:
        job_id = parser.__name__
        if not scheduler.get_job(job_id):
            scheduler.add_job(
                run_parser,
                trigger=trigger,
                args=[parser],
                id=job_id,
                name=parser.parser_name,
                coalesce=True,
                max_instances=1,
                replace_existing=True,
                next_run_time=dt.now(tz=ZoneInfo(TIMEZONE)),
                misfire_grace_time=None,
            )

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit, asyncio.CancelledError):
        logger.info("Shutting down scheduler...")
    finally:
        scheduler.shutdown(wait=True)
        logger.info("Scheduler shutdown completed.")


if __name__ == "__main__":
    asyncio.run(main())
