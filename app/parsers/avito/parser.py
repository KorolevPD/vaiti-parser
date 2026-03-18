import json
import logging
from pathlib import Path
from random import shuffle

from bs4 import BeautifulSoup
import httpx
import yaml

from app.models import Vacancy
from app.parsers import BaseParser, ProxyRefreshRequired
from app.utils import normalize

from .schemas import SearchConfig
from .storage import get_all_vacancies, save_vacancy

logger = logging.getLogger(__name__)

AVITO_API_URL = "https://www.avito.ru/web/1/js/items"
AVITO_BASE_URL = "https://www.avito.ru"


class AvitoVacanciesParser(BaseParser):
    parser_name = "avito_vacancies"

    def __init__(
        self,
        *args: object,
        config_path: str = "configs/avito_vacancies.yaml",
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._config_path = Path(config_path)

    async def parse_once(self) -> None:
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
            logger.info("Avito search '%s' page %s started", keyword, page)

            response = await self.fetch(AVITO_API_URL, params=params)
            vacancies = self.extract_catalog_items(
                response,
                global_exclude=global_exclude,
                page_exclude=exclude,
            )
            if not vacancies:
                return

            for vacancy in vacancies:
                save_vacancy(vacancy)

            if len(vacancies) < 50:
                return

            page += 1

    async def complete_missing_details(self) -> None:
        vacancies = get_all_vacancies()
        shuffle(vacancies)
        for vacancy in vacancies:
            if vacancy.employment_type:
                continue

            updated = await self.complete_vacancy(vacancy)
            if updated:
                save_vacancy(updated)

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
        response: httpx.Response,
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
        published_at = int(data.get("sortTimeStamp") or 0)

        return Vacancy(
            id=vacancy_id,
            source="avito",
            company_name=company_name,
            company_logo_url=company_logo_url,
            position_title=title,
            raw_text=description,
            location=location,
            city=city,
            source_url=f"{AVITO_BASE_URL}{url_path}",
            salary_raw=salary_raw,
            published_at=published_at,
        )

    async def complete_vacancy(self, vacancy: Vacancy) -> Vacancy | None:
        try:
            response = await self.fetch(vacancy.source_url)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.info(
                    "Vacancy not found anymore: %s", vacancy.source_url
                )
                return None
            raise

        soup = BeautifulSoup(response.text, "html.parser")

        for item in soup.find_all("li"):
            label = item.find("span")
            if label is None:
                continue

            label_text = label.get_text(strip=True)
            raw_value = (
                item.get_text(strip=True).replace(label_text, "").strip()
            )

            if "Формат работы" in label_text:
                vacancy.work_format = raw_value

            if "Занятость" in label_text:
                vacancy.employment_type = raw_value

        description = soup.select_one(
            '[data-marker="item-view/item-description"]'
        )
        if description is not None:
            vacancy.raw_text = description.get_text("\n", strip=True)

        return vacancy
