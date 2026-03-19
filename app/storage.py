from typing import Iterable, Optional, Sequence, Type, TypeVar, Union

from sqlalchemy.inspection import inspect
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.config import settings

T = TypeVar("T", bound=SQLModel)

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
                print(f"Updated: {type(obj).__name__} {pk_values}")
            else:
                session.add(obj)
                print(f"Added: {type(obj).__name__} {pk_values}")

        session.commit()


def get_all(
    model: Type[T], limit: Optional[int] = None, offset: Optional[int] = None
) -> Sequence[T]:
    with get_session() as session:
        stmt = select(model)

        if offset:
            stmt = stmt.offset(offset)

        if limit:
            stmt = stmt.limit(limit)

        return session.exec(stmt).all()
