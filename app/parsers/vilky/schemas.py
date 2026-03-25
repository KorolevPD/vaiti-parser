from typing import List

from pydantic import BaseModel


class Search(BaseModel):
    name: str
    specialization: str
    skills: List[str]
