import html
import json
import logging
from pathlib import Path
from random import shuffle

from bs4 import BeautifulSoup
from curl_cffi import Response
from curl_cffi.requests.exceptions import HTTPError
import yaml

from app.models import Vacancy
from app.parsers import BaseParser, ProxyRefreshRequired
from app.services.kafka_producer import KafkaProducer
from app.storage import delete, get, save
from app.utils import normalize

from .schemas import SearchConfig

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
AVITO_API_URL = "https://www.avito.ru/web/1/js/items"
AVITO_BASE_URL = "https://www.avito.ru"


class AvitoVacanciesParser(BaseParser):
    parser_name = "avito_vacancies"

    def __init__(
        self,
        *args: object,
        config_path: str = "config.yaml",
        **kwargs: object,
    ) -> None:
        super().__init__(
            request_delay_range=(2.0, 5.0), *args, **kwargs  # type: ignore
        )
        self._config_path = BASE_DIR / config_path
        self.kafka_producer_discovered = KafkaProducer("vacancy.discovered")
        self.kafka_producer_archived = KafkaProducer("vacancy.archived")

    async def parse_once(self) -> None:
        await self.fetch(AVITO_BASE_URL)

        config = self.load_config()
        for search in config.all_combinations:
            await self.run_search(search, config.global_exclude)

        await self.complete_missing_details()

    def load_config(self) -> SearchConfig:
        data = yaml.safe_load(self._config_path.read_text(encoding="utf-8"))
        return SearchConfig.model_validate(data)

    async def run_search(
        self,
        search: tuple[str, list[str], list[str]],
        global_exclude: list[str],
    ) -> None:
        keyword, include, exclude = search
        params = self.build_search_params(keyword, include, exclude)
        page = 1

        while True:
            params["p"] = page
            logger.debug("Avito search '%s' page %s started", keyword, page)

            response = await self.fetch(AVITO_API_URL, params=params)
            vacancies = self.extract_catalog_items(
                response,
                global_exclude=global_exclude,
                page_exclude=exclude,
            )
            if not vacancies:
                return

            save(vacancies)

            page += 1

    async def complete_missing_details(self) -> None:
        vacancies = list(get(Vacancy, source="avito"))
        shuffle(vacancies)
        for vacancy in vacancies:
            updated = await self.complete_vacancy(vacancy)
            if updated:
                self.kafka_producer_discovered.send(updated)
                save(updated)
            else:
                self.kafka_producer_archived.send(vacancy)
                delete(vacancy)

        self.kafka_producer_discovered.flush()
        self.kafka_producer_archived.flush()

    def build_search_params(
        self,
        keyword: str,
        include: list[str],
        exclude: list[str],
    ) -> dict[str, str | int]:
        params: dict[str, str | int] = {
            "name": keyword,
            "view": "vacancy",
            "bt": 1,
            "cd": 0,
            "categoryId": 111,
            "verticalCategoryId": 2,
            "rootCategoryId": 110,
            "locationId": 621540,
            "s": 101,
        }

        for index, item in enumerate(include[:3]):
            params[f"params[149569][{index}]"] = item

        for index, item in enumerate(exclude[:3]):
            params[f"params[164865][{index}]"] = item

        return params

    def extract_catalog_items(
        self,
        response: Response,
        *,
        global_exclude: list[str],
        page_exclude: list[str],
    ) -> list[Vacancy]:
        payload = json.loads(response.text)
        raw_items = payload.get("catalog", {}).get("items", [])

        valid_items: list[Vacancy] = []
        missing_url_items = 0

        for data in raw_items:
            if data.get("type") != "item":
                continue
            if data.get("categoryId") != 111:
                continue

            title = data.get("title") or ""
            if not title:
                continue

            if any(
                normalize(word) in normalize(title) for word in global_exclude
            ):
                continue

            description = data.get("description", "")
            if any(
                normalize(word) in normalize(description)
                for word in page_exclude
            ):
                continue

            url_path = data.get("urlPath")
            if not url_path:
                missing_url_items += 1
                continue

            valid_items.append(self.map_item_to_vacancy(data, url_path))

        if raw_items and not valid_items and missing_url_items:
            raise ProxyRefreshRequired(
                "Avito returned items without vacancy URLs; proxy likely stale"
            )

        return valid_items

    def map_item_to_vacancy(
        self,
        data: dict[str, object],
        url_path: str,
    ) -> Vacancy:
        company_name = None
        user_info = data.get("iva", {})
        if isinstance(user_info, dict):
            raw_step = user_info.get("UserInfoStep")
            if isinstance(raw_step, list) and raw_step:
                first_step = raw_step[0]
                if isinstance(first_step, dict):
                    company_name = (
                        first_step.get("payload", {})
                        .get("profile", {})
                        .get("title")
                    )

        company_logo = data.get("userLogo", {})
        company_logo_url = None
        if isinstance(company_logo, dict):
            raw_src = company_logo.get("src")
            if isinstance(raw_src, str):
                company_logo_url = raw_src

        geo = data.get("geo", {})
        location = None
        if isinstance(geo, dict):
            raw_location = geo.get("formattedAddress")
            if isinstance(raw_location, str):
                location = raw_location

        city_data = data.get("location", {})
        city = None
        if isinstance(city_data, dict):
            raw_city = city_data.get("name")
            if isinstance(raw_city, str):
                city = raw_city

        price = data.get("priceDetailed", {})
        salary_raw = None
        if isinstance(price, dict):
            raw_salary = price.get("fullString")
            if isinstance(raw_salary, str):
                salary_raw = raw_salary

        vacancy_id = str(data["id"])
        title = str(data["title"])
        description = str(data.get("description", ""))
        raw_timestamp = data.get("sortTimeStamp")
        published_at = (
            int(raw_timestamp) if isinstance(raw_timestamp, int) else 0
        )

        return Vacancy(
            id=vacancy_id,
            source="avito",
            company_name=company_name,
            company_logo_url=company_logo_url,
            position_title=title,
            raw_text=description,
            location=location,
            city=city,
            source_url=f"{AVITO_BASE_URL}{url_path}".split("?")[0],
            salary_raw=salary_raw,
            published_at=published_at,
        )

    async def complete_vacancy(self, vacancy: Vacancy) -> Vacancy | None:
        try:
            url = vacancy.source_url.replace(
                AVITO_BASE_URL, "https://www.avito.ru/items/ads"
            )
            r = await self.fetch(url)
        except HTTPError as e:
            if e.response.status_code == 404:
                logger.debug(
                    "Vacancy not found anymore: %s", vacancy.source_url
                )
                return None
            raise

        data = json.loads(r.text)
        items = data.get("buyerItem", {}).get("paramsBlock", {}).get("items")

        if items:
            for item in items:
                title = item.get("title")
                description = item.get("description")
                if "Формат работы" in title:
                    work_formats = None
                    if isinstance(description, str):
                        work_formats = description.split(",")
                    vacancy.work_formats = work_formats
                if "Занятость" in title:
                    employment_types = None
                    if isinstance(description, str):
                        employment_types = description.split(",")
                    vacancy.employment_types = employment_types

        description = (
            data.get("buyerItem", {}).get("item", {}).get("description")
        )
        if description:
            vacancy.raw_text = BeautifulSoup(
                html.unescape(description), "html.parser"
            ).get_text(separator="\n", strip=True)

        vacancy.source_url = vacancy.source_url.split("?")[0]

        return vacancy
