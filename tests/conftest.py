"""Keep test results independent of a developer's saved TermDoctor settings."""

import pytest

from termdoctor import i18n
from termdoctor.education import set_active_mode


@pytest.fixture(autouse=True)
def isolated_termdoctor_preferences(monkeypatch, tmp_path):
    # User environment variables and ~/.termdoctor/config.json must not
    # determine the expected output of unrelated CLI regression tests.
    monkeypatch.setenv("TERMDOCTOR_LANG", "en")
    monkeypatch.delenv("TERMDOCTOR_MODE", raising=False)
    config_dir = tmp_path / ".termdoctor"
    monkeypatch.setattr(i18n, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(i18n, "CONFIG_FILE", config_dir / "config.json")
    i18n.set_locale("en")
    set_active_mode("standard")
    yield
    i18n.set_locale("en")
    set_active_mode("standard")
