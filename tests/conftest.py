import httpx
import pytest


class DummyHttpClient:
    async def get(self, *args: object, **kwargs: object) -> httpx.Response:
        raise NotImplementedError


@pytest.fixture()
async def dummy_http_client() -> DummyHttpClient:
    return DummyHttpClient()
