from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
    )


class Company(BaseSchema):
    id: UUID
    name: str
    aliases: List[str] = Field(default_factory=list)


class CompanyResponse(BaseSchema):
    content: List[Company]
    totalElements: int
    totalPages: int
    number: int
    size: int
