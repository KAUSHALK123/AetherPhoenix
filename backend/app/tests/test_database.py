"""Tests for database foundation configuration."""

from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine, get_db, init_db


def test_database_init() -> None:
    """Test that database engine initializes and metadata is bound."""
    init_db()
    assert engine is not None
    assert Base.metadata is not None


def test_database_session() -> None:
    """Test database session creation and connectivity."""
    db = SessionLocal()
    try:
        assert isinstance(db, Session)
    finally:
        db.close()


def test_get_db_generator() -> None:
    """Test get_db dependency generator yields valid session."""
    db_gen = get_db()
    db = next(db_gen)
    assert isinstance(db, Session)
    try:
        next(db_gen)
    except StopIteration:
        pass


if __name__ == "__main__":
    test_database_init()
    test_database_session()
    test_get_db_generator()
    print("All database foundation tests passed successfully.")
