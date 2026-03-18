import json
from pathlib import Path
from random import shuffle
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup
from httpx import HTTPStatusError
import yaml

from app.models import Vacancy
from app.parsers import BaseParser
from app.utils import normalize

from .schemas import SearchConfig
from .storage import get_all_vacancies, save_vacancy


class AvitoVacanciesParser(BaseParser):
    async def parse(self) -> None:
        config = self.load_config()
        for search in config.all_combinations:
            await self.run_search(search, config.global_exclude)

        vacancies = get_all_vacancies()
        shuffle(vacancies)
        for vacancy in vacancies:
            if vacancy.employment_type:
                continue
            updated = await self.complete_vacancy(vacancy)
            if updated:
                save_vacancy(updated)

    def load_config(
        self, path: str = "configs/avito_vacancies.yaml"
    ) -> SearchConfig:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return SearchConfig(**data)

    async def run_search(
        self,
        search: Tuple[str, List[str], List[str]],
        global_exclude: List[str],
    ) -> None:

        keyword, include, exclude = search

        page = 1
        params = {
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

        for indx, item in enumerate(include[:3]):
            params[f"params[149569][{indx}]"] = item

        for indx, item in enumerate(exclude[:3]):
            params[f"params[164865][{indx}]"] = item

        while True:
            params["p"] = page

            print(f"Start '{keyword}' page {params['p']}")

            r = await self.fetch("https://www.avito.ru/web/1/js/items", params)
            vacancies = json.loads(r.text).get("catalog", {}).get("items", [])

            if not vacancies:
                return

            for data in vacancies:
                if data.get("type") != "item":
                    continue
                if data.get("categoryId") != 111:
                    return

                title = data.get("title")
                if any(
                    normalize(word) in normalize(title)
                    for word in global_exclude
                ):
                    continue

                description = data.get("description", "")
                if any(
                    normalize(word) in normalize(description)
                    for word in exclude
                ):
                    continue

                url_path = data.get("urlPath")
                if not url_path:
                    continue

                company_name = None
                user_info = data.get("iva", {}).get("UserInfoStep")
                if user_info:
                    company_name = (
                        user_info[0]
                        .get("payload", {})
                        .get("profile", {})
                        .get("title")
                    )

                company_logo_url = data.get("userLogo", {}).get("src", None)
                vacancy = Vacancy(
                    id=str(data.get("id")),
                    company_name=company_name,
                    company_logo_url=company_logo_url,
                    position_title=title,
                    raw_text=description,
                    location=data.get("geo", {}).get("formattedAddress"),
                    city=data.get("location", {}).get("name"),
                    source_url=f"https://www.avito.ru{url_path}",
                    salary_raw=data.get("priceDetailed", {}).get("fullString"),
                    published_at=data.get("sortTimeStamp"),
                )
                save_vacancy(vacancy)

                print(f"Item added: {title}")

            if len(vacancies) < 50:
                return

            page += 1

    async def complete_vacancy(self, v: Vacancy) -> Optional[Vacancy]:
        try:
            r = await self.fetch(v.source_url)
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                print(f"Item not found: {v.position_title}")
            else:
                raise

        soup = BeautifulSoup(r.text, "html.parser")

        # Занятость и Способ оформления
        for li in soup.find_all("li"):
            label = li.find("span")
            if not label:
                continue

            label_text = label.get_text(strip=True)
            raw = li.get_text(strip=True).replace(label_text, "").strip()

            if "Формат работы" in label_text:
                v.work_format = raw

            if "Занятость" in label_text:
                v.employment_type = raw

        # Описание
        desc = soup.select_one('[data-marker="item-view/item-description"]')
        description = desc.get_text("\n", strip=True) if desc else None
        if description:
            v.raw_text = description

        return v
