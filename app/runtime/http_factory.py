from curl_cffi.requests import AsyncSession, Response

from app.proxy.client import SharedHttpClient
from app.runtime.state import get_proxy_controller


def create_http_client(proxy: str | None) -> AsyncSession[Response]:
    return AsyncSession(
        proxy=proxy,
        impersonate="chrome",
        http_version="v2",
        timeout=60,
        max_clients=1,
    )


def create_shared_client(
    raw_client: AsyncSession[Response],
) -> SharedHttpClient:
    return SharedHttpClient(
        raw_client,
        proxy_controller=get_proxy_controller(),
    )
