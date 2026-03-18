from functools import cached_property
from itertools import product
from typing import List, Tuple

from pydantic import BaseModel


class SearchGroup(BaseModel):
    keywords: List[str]
    include_any: List[List[str]] = []
    exclude: List[str] = []

    @cached_property
    def combinations(self) -> List[Tuple[str, List[str], List[str]]]:
        if not self.include_any:
            return [(keyword, [], self.exclude) for keyword in self.keywords]

        return [
            (keyword, include, self.exclude)
            for keyword, include in product(self.keywords, self.include_any)
        ]


class SearchConfig(BaseModel):
    global_exclude: List[str] = []
    search_groups: List[SearchGroup]

    @cached_property
    def all_combinations(self) -> List[Tuple[str, List[str], List[str]]]:
        result = []
        for group in self.search_groups:
            result.extend(group.combinations)
        return result
