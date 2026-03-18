import csv
from typing import List

from sqlmodel import Session, create_engine, select

from app.core.config import settings
from app.models import Vacancy

engine = create_engine(settings.DATABASE_URL, echo=False)


def save_vacancy(v: Vacancy) -> None:
    with Session(engine) as session:
        existing = session.get(Vacancy, v.id)
        if existing:
            for field, value in v.model_dump(exclude_unset=True).items():
                setattr(existing, field, value)
            session.add(existing)
            msg = f"Item updated: {v.position_title}"
        else:
            session.add(v)
            msg = f"Item added: {v.position_title}"
        session.commit()
        print(msg)


def get_all_vacancies() -> List[Vacancy]:
    with Session(engine) as session:
        statement = select(Vacancy)
        results = session.exec(statement)
        return list(results.all())


def export_vacancies_to_csv(vacancies: List[Vacancy]) -> None:
    if not vacancies:
        return

    fieldnames = vacancies[0].model_dump().keys()

    with open("out.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for vacancy in vacancies:
            writer.writerow(vacancy.model_dump())
