import pytest
from persistent_store import configured, save_observations, load_observations


def test_database_disabled_by_default():
    assert not configured({})
    assert configured({'DATABASE_URL':'postgresql://example.invalid/db'})


def test_no_silent_local_fallback(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with pytest.raises(RuntimeError, match='not configured'):
        save_observations([])
    with pytest.raises(RuntimeError, match='not configured'):
        load_observations()


def test_limit_validation(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://example.invalid/db')
    with pytest.raises(ValueError, match='limit'):
        load_observations(limit=10001)
