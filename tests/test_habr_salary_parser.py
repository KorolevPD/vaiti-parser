from typing import Any, Dict

import pytest

from app.models import Currency
from app.parsers.habr import parser as habr_parser_module
from app.parsers.habr.parser import HABR_API_URL, HabrSalaryParser
from tests.conftest import DummyHttpClient


class FakeResponse:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self.payload = payload

    def json(self) -> Dict[str, Any]:
        return self.payload


def build_parser() -> HabrSalaryParser:
    return HabrSalaryParser(
        DummyHttpClient(),
        proxy_controller=None,
        run_interval_seconds=1,
    )


def test_build_salaries_skips_all_group_and_maps_fields() -> None:
    parser = build_parser()

    salaries = parser.build_salaries(
        {
            "groups": [
                {
                    "name": "All",
                    "seoTitle": ["ignored"],
                    "min": 0,
                    "max": 0,
                },
                {
                    "name": "Junior",
                    "seoTitle": ["Python developer"],
                    "min": 120000,
                    "max": 180000,
                },
                {
                    "name": "Middle",
                    "seoTitle": ["Python developer"],
                    "min": 220000,
                    "max": 320000,
                },
            ]
        },
        specialization="python",
    )

    assert len(salaries) == 2

    junior = salaries[0]
    assert junior.source == "habr"
    assert junior.external_title == "Python developer"
    assert junior.external_grade == "Junior"
    assert junior.external_specialization == "python"
    assert junior.salary_min == 120000
    assert junior.salary_max == 180000
    assert junior.currency == Currency.RUB

    middle = salaries[1]
    assert middle.external_grade == "Middle"
    assert middle.salary_min == 220000
    assert middle.salary_max == 320000


def test_build_salaries_returns_empty_list_without_groups() -> None:
    parser = build_parser()

    salaries = parser.build_salaries({}, specialization="python")

    assert salaries == []


@pytest.mark.asyncio
async def test_parse_once_fetches_aliases_and_saves_built_salaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parser = build_parser()
    fetch_calls: list[tuple[str, Dict[str, Any]]] = []
    saved_batches: list[list[object]] = []

    responses: Dict[tuple[str, str | None], Dict[str, Any]] = {
        (f"{HABR_API_URL}/specializations", None): {
            "groups": [
                {
                    "items": [
                        {"alias": "python"},
                        {"alias": "golang"},
                    ]
                }
            ]
        },
        (
            f"{HABR_API_URL}/salary_calculator/general_graph",
            "python",
        ): {
            "groups": [
                {
                    "name": "Junior",
                    "seoTitle": ["Python developer"],
                    "min": 100000,
                    "max": 150000,
                }
            ]
        },
        (
            f"{HABR_API_URL}/salary_calculator/general_graph",
            "golang",
        ): {
            "groups": [
                {
                    "name": "All",
                    "seoTitle": ["Go developer"],
                    "min": 0,
                    "max": 0,
                }
            ]
        },
    }

    async def fake_fetch(url: str, **kwargs: object) -> FakeResponse:
        params = kwargs.get("params")
        fetch_calls.append((url, kwargs))
        alias = None
        if isinstance(params, dict):
            alias = params.get("spec_aliases[]")
        return FakeResponse(responses[(url, alias)])

    def fake_save(items: object) -> None:
        saved_batches.append(
            list(items) if isinstance(items, (list, tuple)) else []
        )

    def keep_order(_: list[str]) -> None:
        return None

    monkeypatch.setattr(parser, "fetch", fake_fetch)
    monkeypatch.setattr(habr_parser_module, "save", fake_save)
    monkeypatch.setattr(habr_parser_module, "shuffle", keep_order)

    await parser.parse_once()

    assert fetch_calls == [
        (f"{HABR_API_URL}/specializations", {}),
        (
            f"{HABR_API_URL}/salary_calculator/general_graph",
            {"params": {"spec_aliases[]": "python"}},
        ),
        (
            f"{HABR_API_URL}/salary_calculator/general_graph",
            {"params": {"spec_aliases[]": "golang"}},
        ),
    ]

    assert len(saved_batches) == 2

    salaries = saved_batches[0]
    assert len(salaries) == 1
    assert salaries[0].external_title == "Python developer"  # type: ignore
    assert salaries[0].external_specialization == "python"  # type: ignore

    assert saved_batches[1] == []
