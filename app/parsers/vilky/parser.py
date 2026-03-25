import logging
from pathlib import Path
from typing import List

import yaml

from app.parsers import BaseParser

from .schemas import Search

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
VILKY_BASE_URL = ""


class VilkySalaryParser(BaseParser):
    parser_name = "dreamjob_ratings"

    def __init__(
        self,
        *args: object,
        config_path: str = "config.yaml",
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)  # type: ignore
        self._config_path = BASE_DIR / config_path

    async def parse_once(self) -> None:
        await self.fetch(VILKY_BASE_URL)
        searches = self.load_searches()
        for search in searches:
            pass

    def load_searches(self) -> List[Search]:
        searches = yaml.safe_load(
            self._config_path.read_text(encoding="utf-8")
        )
        return [Search.model_validate(s) for s in searches]
