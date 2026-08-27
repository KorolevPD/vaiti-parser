from datetime import datetime as dt
import html
import logging
from random import shuffle
from typing import Any, Dict, List

from bs4 import BeautifulSoup, ResultSet, Tag
from curl_cffi.requests.exceptions import HTTPError

from app.models import Rating, Salary, Vacancy, WorkFormat
from app.parsers import BaseParser
from app.services.kafka_producer import KafkaProducer
from app.storage import delete, get, save

logger = logging.getLogger(__name__)

HABR_BASE_URL = "https://career.habr.com"
HABR_API_URL = f"{HABR_BASE_URL}/api"

# fmt: off
HABR_SPECIALIZATIONS = (
    1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22,
    23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 36, 37, 41, 42, 43, 44, 72,
    73, 75, 76, 77, 78, 79, 80, 81, 82, 83, 85, 86, 87, 89, 90, 91, 92, 93, 94,
    95, 96, 97, 98, 99, 100, 106, 107, 108, 109, 110, 111, 118, 119, 122, 125,
    126, 129, 130, 168, 172, 173, 174, 175, 176, 177, 182, 183, 185, 186, 187,
    188
)
# fmt: on


class HarbRatingParser(BaseParser):
    parser_name = "habr_rating"

    def __init__(
        self,
        *args: object,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)  # type: ignore
        self.kafka_producer = KafkaProducer("rating.discovered")

    async def parse_once(self) -> None:
        page = 1
        max_page = 100

        while page <= max_page:

            r = await self.fetch(
                f"{HABR_BASE_URL}/companies",
                params={"page": page, "with_ratings": 1},
            )

            soup = BeautifulSoup(r.text, "html.parser")

            companies = soup.select(".companies-item")

            if not companies:
                break

            ratings = self.build_ratings(companies)
            self.kafka_producer.send(ratings)
            save(ratings)

            page += 1

        self.kafka_producer.flush()

    def build_ratings(self, companies: ResultSet[Tag]) -> List[Rating]:
        ratings = []

        for company in companies:
            name_tag = company.select_one(".companies-item-name .title")
            rating_tag = company.select_one(
                ".companies-item-name__rating .rating"
            )

            if not (name_tag and rating_tag):
                continue

            rating = Rating(
                source="habr",
                company_name=name_tag.text.strip(),
                rating=float(rating_tag.text.strip()),
            )

            ratings.append(rating)

        return ratings


class HabrSalaryParser(BaseParser):
    parser_name = "habr_salaries"

    def __init__(
        self,
        *args: object,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)  # type: ignore
        self.kafka_producer = KafkaProducer("salary.discovered")

    async def parse_once(self) -> None:
        r = await self.fetch(f"{HABR_API_URL}/frontend_v1/specializations")
        data = r.json()  # type: ignore
        aliases = [
            item["alias"]
            for group in data.get("groups", [])
            for item in group.get("items", [])
        ]
        shuffle(aliases)

        for alias in aliases:
            r = await self.fetch(
                f"{HABR_API_URL}/frontend_v1/salary_calculator/general_graph",
                params={"spec_aliases[]": alias},
            )
            salaries = self.build_salaries(r.json(), alias)  # type: ignore
            self.kafka_producer.send(salaries)
            save(salaries)

        self.kafka_producer.flush()

    def build_salaries(
        self, data: Dict[str, Any], specialization: str
    ) -> List[Salary]:
        salaries = []

        for item in data.get("groups", []):
            if item.get("name") == "All":
                continue

            salary = Salary(
                source="habr",
                external_title=item["seoTitle"][0],
                external_grade=item["name"],
                external_specialization=specialization,
                salary_min=item["min"],
                salary_max=item["max"],
            )

            salaries.append(salary)

        return salaries


class HabrVacancyParser(BaseParser):
    parser_name = "habr_vacancy"

    def __init__(
        self,
        *args: object,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)  # type: ignore
        self.kafka_producer_discovered = KafkaProducer("vacancy.discovered")
        self.kafka_producer_archived = KafkaProducer("vacancy.archived")

    async def parse_once(self) -> None:
        await self.fetch(HABR_BASE_URL)
        await self.run_simple_search()
        await self.complete_missing_details()

        self.kafka_producer_discovered.flush()
        self.kafka_producer_archived.flush()

    async def run_simple_search(self) -> None:
        page = 1
        max_page = 1

        while page <= max_page:
            r = await self.fetch(
                f"{HABR_API_URL}/frontend/vacancies",
                params={
                    "page": page,
                    "s[]": HABR_SPECIALIZATIONS,
                },
            )
            vacancies_json = r.json()  # type: ignore
            max_page = vacancies_json.get("meta", {}).get("totalPages", 0)
            vacancies = self.extract_vacancies(vacancies_json)
            save(vacancies)

            page += 1

    def extract_vacancies(
        self, vacancies_json: Dict[str, Any]
    ) -> list[Vacancy]:
        vacancies: list[Vacancy] = []
        raw_items = vacancies_json.get("list", [])

        for data in raw_items:
            vacancy_id = data.get("id")
            if not vacancy_id:
                continue

            company_data = data.get("company", {})

            salary_data = data.get("salary", {})
            currency = salary_data.get("currency")
            if currency:
                currency = currency.replace("rur", "RUB").upper()

            employment_type = data.get("employment")

            if data.get("remoteWork"):
                work_format = WorkFormat.REMOTE
            else:
                work_format = WorkFormat.OFFICE

            locations = data.get("locations") or []
            locations_str = (
                ", ".join([loc.get("title") for loc in locations])
                if locations
                else None
            )

            date_str = data.get("publishedDate", {}).get("date")

            vacancies.append(
                Vacancy(
                    id=str(vacancy_id),
                    source="habr",
                    company_name=company_data.get("title"),
                    company_logo_url=company_data.get("logo", {}).get("src"),
                    position_title=data.get("title"),
                    raw_text="Отсутствует",
                    city=locations_str,
                    source_url=f"{HABR_BASE_URL}{data.get('href')}",
                    salary_raw=salary_data.get("formatted"),
                    salary_min=salary_data.get("from"),
                    salary_max=salary_data.get("to"),
                    salary_currency=currency,
                    employment_types=employment_type,
                    work_formats=work_format,
                    published_at=int(dt.fromisoformat(date_str).timestamp()),
                )
            )

        return vacancies

    async def complete_missing_details(self) -> None:
        vacancies = list(get(Vacancy, source="habr"))
        shuffle(vacancies)
        for vacancy in vacancies:
            updated = await self.complete_vacancy(vacancy)
            if updated:
                self.kafka_producer_discovered.send(updated)
                save(updated)
            else:
                self.kafka_producer_archived.send(vacancy)
                delete(vacancy)

    async def complete_vacancy(self, vacancy: Vacancy) -> Vacancy | None:
        try:
            r = await self.fetch(vacancy.source_url)
        except HTTPError as e:
            if e.response.status_code == 404:
                logger.debug(
                    "Vacancy not found anymore: %s", vacancy.source_url
                )
                return None
            raise

        soup = BeautifulSoup(r.text, "html.parser")
        description = str(soup.find("div", class_="style-ugc"))

        if description:
            vacancy.raw_text = BeautifulSoup(
                html.unescape(description), "html.parser"
            ).get_text(separator="\n", strip=True)

        return vacancy
