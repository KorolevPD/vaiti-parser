import json

from curl_cffi import Response
import pytest

from app.parsers import ProxyRefreshRequired
from app.parsers.avito.parser import AvitoVacanciesParser
from tests.conftest import DummyHttpClient


def build_parser() -> AvitoVacanciesParser:
    return AvitoVacanciesParser(
        DummyHttpClient(),
        proxy_controller=None,
        run_interval_seconds=1,
    )


def test_extract_catalog_items_maps_vacancy() -> None:
    parser = build_parser()
    response_text = json.dumps(
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
    )
    response = Response(None)
    response.status_code = 200
    response._text = response_text

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
    response_text = json.dumps(
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
    )
    response = Response(None)
    response.status_code = 200
    response._text = response_text

    with pytest.raises(ProxyRefreshRequired):
        parser.extract_catalog_items(
            response,
            global_exclude=[],
            page_exclude=[],
        )
