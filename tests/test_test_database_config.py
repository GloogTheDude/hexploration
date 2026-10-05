import pytest

from tests.database_config import validated_test_database_url


def test_external_test_database_url_is_read_from_environment(monkeypatch):
    url = "postgresql+psycopg://user:password@db.example/hexploration_test"
    monkeypatch.setenv("TEST_DATABASE_URL", url)

    assert validated_test_database_url() == url


def test_external_test_database_url_rejects_the_normal_database(monkeypatch):
    monkeypatch.setenv(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://user:password@db.example/hexploration",
    )

    with pytest.raises(ValueError, match="refuses to use TEST_DATABASE_URL"):
        validated_test_database_url()


def test_missing_external_test_database_url_keeps_sqlite_default(monkeypatch):
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)

    assert validated_test_database_url() is None
