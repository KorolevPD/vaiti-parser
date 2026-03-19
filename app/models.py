from enum import Enum
from typing import Optional

from sqlalchemy import Column, Enum as SAEnum
from sqlmodel import Field, SQLModel


class Currency(str, Enum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"


class Vacancy(SQLModel, table=True):
    id: str = Field(primary_key=True)
    source: str
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

    grade_id: Optional[str] = None
    specialization_id: Optional[str] = None
    domain_id: Optional[str] = None
    skill_ids: Optional[str] = None
    tool_ids: Optional[str] = None
    embedding: Optional[str] = None
    attributes: Optional[str] = None


class Salary(SQLModel, table=True):
    source: str = Field(primary_key=True)
    title: str = Field(primary_key=True)
    grade: str = Field(primary_key=True)
    specialization: str
    salary_min: int
    salary_max: int
    salary_currency: Currency = Field(
        default=Currency.RUB, sa_column=Column(SAEnum(Currency))
    )


class Rating(SQLModel, table=True):
    id: str = Field(primary_key=True)
    company_id: str
    rating: float
