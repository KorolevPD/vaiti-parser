from functools import cached_property
from itertools import product

from pydantic import BaseModel, Field


class SearchGroup(BaseModel):
    keywords: list[str]
    include_any: list[list[str]] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)

    @cached_property
    def combinations(self) -> list[tuple[str, list[str], list[str]]]:
        if not self.include_any:
            return [(keyword, [], self.exclude) for keyword in self.keywords]

        return [
            (keyword, include, self.exclude)
            for keyword, include in product(self.keywords, self.include_any)
        ]


class SearchConfig(BaseModel):
    global_exclude: list[str] = Field(default_factory=list)
    search_groups: list[SearchGroup]

    @cached_property
    def all_combinations(self) -> list[tuple[str, list[str], list[str]]]:
        result: list[tuple[str, list[str], list[str]]] = []
        for group in self.search_groups:
            result.extend(group.combinations)
        return result
