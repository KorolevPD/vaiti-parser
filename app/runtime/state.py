import logging
from typing import Optional

from mobileproxy import Client

from app.core.config import settings
from app.proxy.manager import ProxyController
from app.proxy.models import ProxyConfig
from app.proxy.provider import MobileProxyProvider

logger = logging.getLogger(__name__)
_proxy_controller: Optional[ProxyController] = None


def init_proxy_controller(
    controller: Optional[ProxyController] = None,
) -> None:
    global _proxy_controller
    if not controller:
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
            controller = ProxyController(
                provider=MobileProxyProvider(proxy_config),
                cooldown_seconds=proxy_config.cooldown_seconds,
            )
        else:
            logger.warning("No proxies found.")
    _proxy_controller = controller


def get_proxy_controller() -> Optional[ProxyController]:
    return _proxy_controller
