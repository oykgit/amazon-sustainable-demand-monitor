import pytest
from secure_database import DatabaseAccessError
from persistent_store import configured, save_observations, load_observations


def test_database_disabled_by_default():
    assert not configured({})
    assert configured({'DATABASE_URL':'postgresql://example.invalid/db'})


def test_no_silent_local_fallback(monkeypatch):
    monkeypatch.setenv('COMMERCIAL_STORAGE_MODE', 'legacy')
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with pytest.raises(DatabaseAccessError, match='Legacy database configuration missing'):
        save_observations([])
    with pytest.raises(DatabaseAccessError, match='Legacy database configuration missing'):
        load_observations()


def test_limit_validation(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://example.invalid/db')
    with pytest.raises(ValueError, match='limit'):
        load_observations(limit=10001)
