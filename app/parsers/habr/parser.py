from random import shuffle
from typing import Any, Dict, List

from app.models import Salary
from app.parsers import BaseParser
from app.storage import save

HABR_API_URL = "https://career.habr.com/api/frontend_v1"


class HabrSalaryParser(BaseParser):
    parser_name = "habr_salaries"

    def __init__(
        self,
        *args: object,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)  # type: ignore

    async def parse_once(self) -> None:
        r = await self.fetch(f"{HABR_API_URL}/specializations")
        data = r.json()
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
            salaries = self.build_salaries(r.json(), alias)
            save(salaries)

    def build_salaries(
        self, data: Dict[str, Any], specialization: str
    ) -> List[Salary]:
        salaries = []

        for item in data.get("groups", []):
            if item.get("name") == "All":
                continue

            salary = Salary(
                source="habr",
                title=item["seoTitle"][0],
                grade=item["name"],
                specialization=specialization,
                salary_min=item["min"],
                salary_max=item["max"],
            )

            salaries.append(salary)

        return salaries


class HarbRatingParser(BaseParser):
    pass
