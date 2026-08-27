import logging
import sys

from app.core.config import settings


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
        level=logging.INFO if settings.DEBUG else logging.WARNING,
        handlers=[handler],
    )
