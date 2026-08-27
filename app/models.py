from enum import StrEnum
from time import time
from typing import Dict, Iterable, List, Optional, TypeVar, Union

from pydantic import computed_field, field_validator
from pydantic.alias_generators import to_camel
from sqlalchemy import JSON, Column, Enum as SAEnum
from sqlmodel import BigInteger, Field, SQLModel

from app.core.config import settings

EnumT = TypeVar("EnumT", bound=StrEnum)


class BaseSQLModel(SQLModel):
    model_config = {
        "validate_by_name": True,
        "alias_generator": to_camel,
        "validate_assignment": True,
    }

    __table_args__ = {"schema": settings.database_schema}


class Currency(StrEnum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"


class WorkFormat(StrEnum):
    REMOTE = "REMOTE"
    OFFICE = "OFFICE"
    HYBRID = "HYBRID"


class EmploymentType(StrEnum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    PROJECT = "PROJECT"
    CONTRACT = "CONTRACT"
    FREELANCE = "FREELANCE"
    INTERNSHIP = "INTERNSHIP"


def _build_alias_map(data: Dict[EnumT, Iterable[str]]) -> Dict[str, EnumT]:
    result: Dict[str, EnumT] = {}

    for enum_value, aliases in data.items():
        result[enum_value.value.lower()] = enum_value

        for alias in aliases:
            result[alias.strip().lower()] = enum_value

    return result


WORK_FORMAT_ALIASES = _build_alias_map(
    {
        WorkFormat.REMOTE: ["Удалённо"],
        WorkFormat.OFFICE: ["В офисе или на объекте"],
        WorkFormat.HYBRID: ["Гибрид"],
    }
)

EMPLOYMENT_TYPE_ALIASES = _build_alias_map(
    {
        EmploymentType.FULL_TIME: ["Полная"],
        EmploymentType.PART_TIME: ["Частичная"],
        EmploymentType.CONTRACT: ["Временная"],
    }
)


class Vacancy(BaseSQLModel, table=True):
    __tablename__ = "vacancies"

    id: str = Field(primary_key=True)
    source: str = Field(primary_key=True)
    company_name: Optional[str] = None
    company_logo_url: Optional[str] = None
    position_title: Optional[str] = None
    raw_text: str
    location: Optional[str] = None
    city: Optional[str] = None
    source_url: str
    salary_raw: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    salary_gross: Optional[bool] = None
    work_formats: Optional[List[str]] = Field(None, sa_column=Column(JSON))
    employment_types: Optional[List[str]] = Field(None, sa_column=Column(JSON))
    published_at: int = Field(sa_type=BigInteger)

    @computed_field
    def external_id(self) -> str:
        return self.id

    @field_validator("work_formats", mode="before")
    @classmethod
    def validate_work_formats(cls, v: str) -> Optional[List[WorkFormat]]:
        return cls._normalize_enum(v, WORK_FORMAT_ALIASES, WorkFormat)

    @field_validator("employment_types", mode="before")
    @classmethod
    def validate_employment_types(
        cls, v: str
    ) -> Optional[List[EmploymentType]]:
        return cls._normalize_enum(v, EMPLOYMENT_TYPE_ALIASES, EmploymentType)

    @classmethod
    def _normalize_enum(
        cls,
        values: Union[None, str, EnumT, List[Union[str, EnumT]]],
        aliases: Dict[str, EnumT],
        enum_cls: type[EnumT],
    ) -> Optional[List[EnumT]]:
        if values is None:
            return None

        if not isinstance(values, list):
            values = [values]

        result: List[EnumT] = []

        for value in values:
            if isinstance(value, enum_cls):
                result.append(value)
                continue

            if isinstance(value, str):
                normalized = value.strip().lower()
                try:
                    result.append(aliases[normalized])
                except KeyError as e:
                    raise ValueError(f"Unknown enum value: {value}") from e
            else:
                raise TypeError(f"Unsupported type: {type(value)}")

        return result


class Salary(BaseSQLModel, table=True):
    __tablename__ = "salaries"

    source: str = Field(primary_key=True)
    external_title: str = Field(primary_key=True)
    external_grade: str = Field(primary_key=True)
    external_specialization: str
    salary_min: int
    salary_max: int
    currency: Currency = Field(
        default=Currency.RUB, sa_column=Column(SAEnum(Currency))
    )
    company_id: Optional[str] = None
    company_name: Optional[str] = None
    specialization_id: Optional[str] = None
    grade_id: Optional[str] = None
    timestamp: int = Field(
        sa_type=BigInteger, default_factory=lambda: int(time())
    )


class Rating(BaseSQLModel, table=True):
    __tablename__ = "ratings"

    company_id: Optional[str]
    company_name: str = Field(primary_key=True)
    source: str = Field(primary_key=True)
    rating: float
    reviews_count: Optional[int] = None
    timestamp: int = Field(
        sa_type=BigInteger, default_factory=lambda: int(time())
    )
