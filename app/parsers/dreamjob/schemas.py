from typing import List

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class Company(BaseSchema):
    id: str
    name: str
    aliases: List[str] = Field(default_factory=list)


class CompanyResponse(BaseSchema):
    content: List[Company]
    total_elements: int
    total_pages: int
    number: int
    size: int
