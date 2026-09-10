import logging
from collections.abc import Callable, Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)


def build_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy engine for the given database URL.

    The engine is the entry point to the connection pool. One engine per
    process is the expected usage. Do not call this inside request handlers.
    """
    logger.info("Initializing database engine")
    return create_engine(database_url, pool_pre_ping=True)


def build_session_factory(database_url: str) -> sessionmaker[Session]:
    """Create a session factory bound to the given database URL.

    Use this at application startup to produce the factory that get_db
    will draw sessions from. Do not call this inside request handlers.
    """
    engine = build_engine(database_url)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db(session_factory: sessionmaker[Session]) -> Generator[Session]:
    """Yield a database session and close it after the request completes.

    Inject this via FastAPI's Depends mechanism. Never instantiate a session
    directly inside a route handler or service.

    Args:
        session_factory: The sessionmaker instance built at application startup.

    Yields:
        An active SQLAlchemy Session scoped to the current request.
    """
    with session_factory() as session:
        yield session


def make_get_db(
    session_factory: sessionmaker[Session],
) -> Callable[[], Generator[Session]]:
    """Return a zero-argument FastAPI dependency that yields a database session.

    Use this to produce a dependency suitable for dependency_overrides without
    requiring session_factory as a parameter. Bind this at application startup.

    Args:
        session_factory: The sessionmaker instance built at application startup.

    Returns:
        A zero-argument callable that yields an active SQLAlchemy Session.
    """

    def _get_db() -> Generator[Session]:
        with session_factory() as session:
            yield session

    return _get_db
