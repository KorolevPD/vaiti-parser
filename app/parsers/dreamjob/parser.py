import logging
from random import shuffle
from typing import List, Optional

from bs4 import BeautifulSoup

from app.models import Rating
from app.parsers import BaseParser
from app.services.kafka_producer import KafkaProducer
from app.storage import save

from .schemas import Company, CompanyResponse

logger = logging.getLogger(__name__)

DREAMJOB_BASE_URL = "https://dreamjob.ru"
COMPANY_SERVICE_URL = "http://company-service:8080"


class DreamjobRatingParser(BaseParser):
    parser_name = "dreamjob_ratings"

    def __init__(
        self,
        *args: object,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)  # type: ignore
        self.kafka_producer = KafkaProducer("rating.discovered")

    async def parse_once(self) -> None:
        await self.fetch(DREAMJOB_BASE_URL)
        companies = await self.get_companies()
        shuffle(companies)
        for company in companies:
            rating = await self.search(company)
            if rating:
                self.kafka_producer.send(rating)
                save(rating)

        self.kafka_producer.flush()

    async def get_companies(self) -> List[Company]:
        page = 1
        max_page = 10000
        companies: List[Company] = []
        while page <= max_page:
            r = await self.fetch(
                f"{COMPANY_SERVICE_URL}/internal/companies/dictionary",
                params={"page": page, "size": 100},
            )
            data = CompanyResponse.model_validate(r.json())  # type: ignore

            companies.extend(data.content)
            max_page = data.total_pages
            page += 1

        return companies

    async def search(self, company: Company) -> Optional[Rating]:
        names = [company.name, *company.aliases]
        for name in names:
            r = await self.fetch(
                f"{DREAMJOB_BASE_URL}/site/search",
                params={"query": name},
            )
            rating = await self.fetch_rating(company, r.text)
            if rating:
                return rating
        return None

    async def fetch_rating(
        self, company: Company, html: str
    ) -> Optional[Rating]:
        soup = BeautifulSoup(html, "html.parser")
        card = soup.select_one(".industry-card")

        if not card:
            return None

        name_element = card.select_one(".industry-card__name")
        rating_element = card.select_one(".sb-rating__value")
        reviews_element = card.select_one(".industry-card__review-link")

        if not (
            name_element
            and (rating_element and rating_element.contents)
            and reviews_element
        ):
            return None

        try:
            rating = float(str(rating_element.contents[0]).strip())
        except ValueError:
            return None

        return Rating(
            company_id=company.id,
            source="dreamjob",
            company_name=name_element.get_text(strip=True),
            rating=rating,
            reviews_count=int(reviews_element.get_text(strip=True)),
        )
