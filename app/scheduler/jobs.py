from datetime import datetime as dt
import logging

from httpx import Client
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from app.core.config import settings
from app.parsers import BaseParser
from app.runtime.http_factory import create_http_client, create_shared_client
from app.runtime.state import get_proxy_controller

logger = logging.getLogger(__name__)


def telegram_error_callback(retry_state: RetryCallState) -> None:
    if not settings.BOT_NOTIFICATION_URL:
        return

    exception = (
        retry_state.outcome.exception() if retry_state.outcome else None
    )
    parser_class = retry_state.kwargs.get("parser_class") or (
        retry_state.args[0] if retry_state.args else None
    )
    parser_name = getattr(parser_class, "__name__", "no_name")

    error_text = (
        "❌ <b>Задача не выполнена</b>\n\n"
        f"Задача: <code>{parser_name}</code>\n"
        f"Время: {dt.now():%Y-%m-%d %H:%M:%S}\n\n"
        f"Последняя ошибка:\n"
        f"<pre>{type(exception).__name__}: {exception}</pre>"
    )

    try:
        with Client(timeout=5) as client:
            r = client.post(
                settings.BOT_NOTIFICATION_URL,
                json={
                    "user_ids": settings.BOT_NOTIFICATION_USERS,
                    "message": error_text,
                },
            )
            r.raise_for_status()
        logger.info("Уведомление об ошибке отправлено в Telegram")
    except Exception:
        logger.warning("Не удалось отправить уведомление в Telegram")
    finally:
        if exception:
            raise exception


@retry(
    stop=stop_after_attempt(2),
    wait=wait_fixed(180),
    retry=retry_if_exception_type(Exception),
    retry_error_callback=telegram_error_callback,
    reraise=True,
)
async def run_parser(parser_class: type[BaseParser]) -> None:
    proxy = None

    proxy_controller = get_proxy_controller()
    if proxy_controller:
        proxy = proxy_controller.proxy_url

    async with create_http_client(proxy) as raw_client:
        shared_client = create_shared_client(raw_client)

        parser = parser_class(
            http_client=shared_client,
            proxy_controller=proxy_controller,
        )

        await parser.parse_once()
