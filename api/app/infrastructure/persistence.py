from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.orm import Session as SQLAlchemySession

from app.infrastructure.config import Settings, get_settings


class Base(DeclarativeBase):
    pass


def create_db_engine(settings: Settings) -> Engine:
    return create_engine(settings.database_url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[SQLAlchemySession]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@lru_cache(maxsize=1)
def get_db_engine() -> Engine:
    return create_db_engine(get_settings())


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[SQLAlchemySession]:
    return create_session_factory(get_db_engine())


def iter_session() -> Iterator[SQLAlchemySession]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
