from dataclasses import dataclass


@dataclass(frozen=True)
class ProxyCredentials:
    username: str
    password: str


@dataclass(frozen=True)
class ProxyConfig:
    url: str
    credentials: ProxyCredentials | None = None
    rotate_url: str | None = None
    cooldown_seconds: float = 120
