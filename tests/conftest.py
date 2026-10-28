"""Make tests deterministic regardless of the developer's saved language."""
import pytest


@pytest.fixture(autouse=True)
def default_test_locale(monkeypatch):
    monkeypatch.setenv("TERMDOCTOR_LANG", "en")
