from random import shuffle
from typing import Any, Dict, List

from bs4 import BeautifulSoup, ResultSet, Tag
from confluent_kafka import Producer

from app.core.config import settings
from app.models import Rating, Salary
from app.parsers import BaseParser
from app.storage import save

HABR_BASE_URL = "https://career.habr.com"
HABR_API_URL = f"{HABR_BASE_URL}/api/frontend_v1"


class HabrSalaryParser(BaseParser):
    parser_name = "habr_salaries"

    def __init__(
        self,
        *args: object,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)  # type: ignore
        self.kafka_producer = None
        if settings.KAFKA_URL:
            self.kafka_producer = Producer(
                {"bootstrap.servers": settings.KAFKA_URL}
            )

    async def parse_once(self) -> None:
        r = await self.fetch(f"{HABR_API_URL}/specializations")
        data = r.json()  # type: ignore
        aliases = [
            item["alias"]
            for group in data.get("groups", [])
            for item in group.get("items", [])
        ]
        shuffle(aliases)

        for alias in aliases:
            r = await self.fetch(
                f"{HABR_API_URL}/salary_calculator/general_graph",
                params={"spec_aliases[]": alias},
            )
            salaries = self.build_salaries(r.json(), alias)  # type: ignore
            self.send_to_kafka(salaries)
            save(salaries)

        if self.kafka_producer:
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

    def send_to_kafka(self, salaries: List[Salary]) -> None:
        if self.kafka_producer:
            for s in salaries:
                self.kafka_producer.produce(
                    "salary.discovered",
                    key=f"{s.source}:{s.external_title}:{s.external_grade}",
                    value=s.model_dump_json(),
                )


class HarbRatingParser(BaseParser):
    parser_name = "habr_rating"

    def __init__(
        self,
        *args: object,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)  # type: ignore
        self.kafka_producer = None
        if settings.KAFKA_URL:
            self.kafka_producer = Producer(
                {"bootstrap.servers": settings.KAFKA_URL}
            )

    async def parse_once(self) -> None:
        page = 1

        while True:

            r = await self.fetch(
                f"{HABR_BASE_URL}/companies",
                params={"page": page, "with_ratings": 1},
            )

            soup = BeautifulSoup(r.text, "html.parser")

            companies = soup.select(".companies-item")

            if not companies:
                break

            ratings = self.build_ratings(companies)
            self.send_to_kafka(ratings)
            save(ratings)

            page += 1

        if self.kafka_producer:
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

    def send_to_kafka(self, ratings: List[Rating]) -> None:
        if self.kafka_producer:
            for r in ratings:
                self.kafka_producer.produce(
                    "rating.discovered",
                    key=f"{r.source}:{r.company_name}",
                    value=r.model_dump_json(),
                )
