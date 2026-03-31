from enum import Enum
from time import time
from typing import Optional

from pydantic.alias_generators import to_camel
from sqlalchemy import Column, Enum as SAEnum
from sqlmodel import Field, SQLModel


class BaseSQLModel(SQLModel):
    model_config = {
        "validate_by_name": True,
        "alias_generator": to_camel,
    }


class Currency(str, Enum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"


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
    work_format: Optional[str] = None
    employment_type: Optional[str] = None
    published_at: int

    # grade = None
    # specialization = None
    # domain = None
    # skills = None
    # attributes = None
    # embedding = None
    # ai_classification = None
    # force_enrichment = None


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
    timestamp: int = Field(default_factory=lambda: int(time()))


class Rating(BaseSQLModel, table=True):
    __tablename__ = "ratings"

    company_id: Optional[str]
    company_name: str = Field(primary_key=True)
    source: str = Field(primary_key=True)
    rating: float
    reviews_count: Optional[int] = None
    timestamp: int = Field(default_factory=lambda: int(time()))
