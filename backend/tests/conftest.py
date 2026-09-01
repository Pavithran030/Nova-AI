import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
import app.models  # noqa: F401 -- import side effect registers every model on Base.metadata


@pytest.fixture()
def db():
    """A fresh in-memory SQLite DB per test -- fully isolated from the real
    dev nova.db file. Services take `db: Session` as a plain parameter (no
    hidden import of app.database.engine), so handing them a session bound
    to this throwaway engine is enough; no monkeypatching required."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
