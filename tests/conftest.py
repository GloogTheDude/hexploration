from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from db import Base
from db.models import (
    Campaign,
    Character,
    CharacterStatus,
    Expedition,
    ExpeditionCharacter,
    ExpeditionStatus,
    MapHex,
    MapVersion,
    User,
    WorldMap,
)


@pytest.fixture()
def db() -> Session:
    """Fresh isolated SQLAlchemy database for every pytest test.

    This intentionally does not use the developer PostgreSQL database. Service
    tests therefore remain deterministic and can be run with plain ``pytest``.
    """
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def campaign(db: Session) -> Campaign:
    campaign = Campaign(
        name="Pytest Campaign",
        description="Isolated service tests",
        epoch_name="Day 1",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign
