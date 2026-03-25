import logging
from typing import Any, Iterable, Optional, Sequence, Type, TypeVar, Union

from sqlalchemy.inspection import inspect
import sqlmodel
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.config import settings

T = TypeVar("T", bound=SQLModel)
logger = logging.getLogger(__name__)
engine = create_engine(settings.DATABASE_URL, echo=False)


def get_session() -> Session:
    return Session(engine)


def save(objs: Union[SQLModel, Iterable[SQLModel]]) -> None:
    if isinstance(objs, SQLModel):
        objs = [objs]
    else:
        objs = list(objs)

    with get_session() as session:
        for obj in objs:
            mapper = inspect(obj.__class__)
            if mapper is None:
                continue
            pk_fields = mapper.primary_key

            pk_values = {col.name: getattr(obj, col.name) for col in pk_fields}

            existing = session.get(type(obj), tuple(pk_values.values()))

            if existing:
                for field, value in obj.model_dump(exclude_unset=True).items():
                    setattr(existing, field, value)
                session.add(existing)
                logger.info(f"Updated: {type(obj).__name__} {pk_values}")
            else:
                session.add(obj)
                logger.info(f"Added: {type(obj).__name__} {pk_values}")

        session.commit()


def get(
    model: Type[T],
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    **filters: Any,
) -> Sequence[T]:
    with get_session() as session:
        stmt = select(model)

        if limit:
            stmt = stmt.limit(limit)

        if offset:
            stmt = stmt.offset(offset)

        for field, value in filters.items():
            stmt = stmt.where(getattr(model, field) == value)

        return session.exec(stmt).all()


def delete(
    model: Type[T],
    **filters: Any,
) -> int:
    with get_session() as session:
        stmt = sqlmodel.delete(model)

        for field, value in filters.items():
            stmt = stmt.where(getattr(model, field) == value)

        result = session.exec(stmt)
        session.commit()

        return result.rowcount
