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
            columns = {col.key for col in mapper.columns}
            pk_fields = mapper.primary_key

            pk_values = {col.name: getattr(obj, col.name) for col in pk_fields}

            existing = session.get(type(obj), tuple(pk_values.values()))

            if existing:
                for field, value in obj.model_dump(exclude_unset=True).items():
                    if field in columns:
                        setattr(existing, field, value)
                session.add(existing)
                logger.debug(f"Updated: {type(obj).__name__} {pk_values}")
            else:
                session.add(obj)
                logger.debug(f"Added: {type(obj).__name__} {pk_values}")

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
    target: Union[Type[SQLModel], SQLModel, Iterable[SQLModel]],
    **filters: Any,
) -> int:
    if isinstance(target, SQLModel):
        target = [target]

    with get_session() as session:
        if isinstance(target, type) and issubclass(target, SQLModel):
            stmt = sqlmodel.delete(target)
            for field, value in filters.items():
                stmt = stmt.where(getattr(target, field) == value)
            result = session.exec(stmt)
            session.commit()
            return result.rowcount or 0

        if isinstance(target, Iterable):
            count = 0
            for obj in target:
                if not isinstance(obj, SQLModel):
                    raise ValueError("All items must be SQLModel instances")
                session.delete(obj)
                count += 1

            session.commit()
            return count

    raise ValueError("Invalid target")
