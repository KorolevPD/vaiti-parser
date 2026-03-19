import httpx


class DummyHttpClient:
    async def get(self, *args: object, **kwargs: object) -> httpx.Response:
        raise NotImplementedError
