import json

import httpx
import pytest

from app.parsers import ProxyRefreshRequired
from app.parsers.avito.parser import AvitoVacanciesParser


class DummyHttpClient:
    async def get(self, *args: object, **kwargs: object) -> httpx.Response:
        raise NotImplementedError


def build_parser() -> AvitoVacanciesParser:
    return AvitoVacanciesParser(
        DummyHttpClient(),
        proxy_controller=None,
        run_interval_seconds=1,
    )


def test_extract_catalog_items_maps_vacancy() -> None:
    parser = build_parser()
    response = httpx.Response(
        200,
        text=json.dumps(
            {
                "catalog": {
                    "items": [
                        {
                            "type": "item",
                            "categoryId": 111,
                            "id": 123,
                            "title": "Python developer",
                            "description": "Backend platform work",
                            "urlPath": "/moskva/vakansii/python_developer_123",
                            "sortTimeStamp": 1700000000,
                            "location": {"name": "Москва"},
                            "geo": {
                                "formattedAddress": "Москва, Россия",
                            },
                            "priceDetailed": {"fullString": "200 000 ₽"},
                        }
                    ]
                }
            },
        ),
    )

    vacancies = parser.extract_catalog_items(
        response,
        global_exclude=[],
        page_exclude=[],
    )

    assert len(vacancies) == 1
    vacancy = vacancies[0]
    assert vacancy.id == "123"
    assert vacancy.source == "avito"
    assert vacancy.source_url.endswith("python_developer_123")


def test_extract_catalog_items_requests_proxy_refresh_on_missing_urls() -> (
    None
):
    parser = build_parser()
    response = httpx.Response(
        200,
        text=json.dumps(
            {
                "catalog": {
                    "items": [
                        {
                            "type": "item",
                            "categoryId": 111,
                            "id": 123,
                            "title": "Python developer",
                            "description": "Backend platform work",
                        }
                    ]
                }
            },
        ),
    )

    with pytest.raises(ProxyRefreshRequired):
        parser.extract_catalog_items(
            response,
            global_exclude=[],
            page_exclude=[],
        )
