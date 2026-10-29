"""Educational modes, Ukrainian localization and packaging in v0.4.1."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from termdoctor.cli import app
from termdoctor.education import educational_content
from termdoctor.engines.python.engine import PythonEngine
from termdoctor.i18n import normalize_locale, normalize_mode, resolve_mode, set_locale, tr
from termdoctor.models import ParsedError

ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


def _env(home: Path, *, language: str = "en") -> dict[str, str]:
    env = os.environ.copy()
    env.update({"HOME": str(home), "USERPROFILE": str(home), "PYTHONPATH": str(ROOT / "src"),
                "TERMDOCTOR_LANG": language,
                "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
    env.pop("TERMDOCTOR_MODE", None)
    return env


def test_ukrainian_aliases():
    for candidate in ("uk", "ua", "ukr", "UK-UA", "українська", "Ukrainian"):
        assert normalize_locale(candidate) == "uk"
    assert tr("diagnosis.location", locale="uk") == "Місце помилки"


def test_valid_and_invalid_modes():
    assert normalize_mode("beg") == "beginner"
    assert normalize_mode("standart") == "standard"
    with pytest.raises(ValueError):
        normalize_mode("expert")


def test_questions_cover_all_105_rules_in_all_languages():
    rules = PythonEngine().load_rules("en")
    ids = {rule.id for rule in rules}
    assert len(rules) == len(ids) == 105
    for locale in ("en", "ru", "uk"):
        path = ROOT / "src" / "termdoctor" / "education" / f"questions.{locale}.yml"
        questions = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert set(questions) == ids
        assert all(isinstance(q, str) and len(q) > 15 for q in questions.values())


def test_all_standard_mechanisms_are_localized():
    ids = {r.id for r in PythonEngine().load_rules("en")}
    for locale in ("en", "ru", "uk"):
        path = ROOT / "src" / "termdoctor" / "education" / f"mechanisms.{locale}.yml"
        mechanisms = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert set(mechanisms) == ids
        assert all(len(value) > 50 for value in mechanisms.values())


def test_ukrainian_rules_are_all_localized():
    engine = PythonEngine()
    english = {r.id: r for r in engine.load_rules("en")}
    ukrainian = {r.id: r for r in engine.load_rules("uk")}
    assert len(ukrainian) == 105
    for identifier, en in english.items():
        uk = ukrainian[identifier]
        assert uk.title != en.title, identifier
        assert uk.explanation != en.explanation, identifier
        assert uk.causes and uk.fixes
        assert all(isinstance(v, str) and v.strip() for v in [uk.title, uk.explanation, *uk.causes, *uk.fixes])


def _flatten(data, prefix=""):
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            yield from _flatten(value, path)
        else:
            yield path, str(value)


def test_ukrainian_interface_catalog_is_complete_and_placeholders_match():
    path = ROOT / "src" / "termdoctor" / "locales"
    en = dict(_flatten(yaml.safe_load((path / "en.yml").read_text(encoding="utf-8"))))
    uk = dict(_flatten(yaml.safe_load((path / "uk.yml").read_text(encoding="utf-8"))))
    assert en.keys() == uk.keys()
    regex = re.compile(r"\{([\w]+)(?::[^{}]*)?\}")
    for key in en:
        assert set(regex.findall(en[key])) == set(regex.findall(uk[key])), key


def test_beginner_and_standard_are_different_in_approach():
    error = ParsedError(error_type="NameError", message="name 'username' is not defined",
                        raw_text="NameError: name 'username' is not defined",
                        file_path="main.py", line_number=5, extracted={"name": "username"})
    for locale in ("en", "ru", "uk"):
        set_locale(locale)
        rule = PythonEngine().find_rule(error, locale=locale)
        beginner = educational_content(rule, error, "beginner")
        standard = educational_content(rule, error, "standard")
        assert "username" in beginner["question"]
        assert "main.py:5" in beginner["where"]
        assert beginner["causes"] == beginner["actions"] == []
        assert standard["causes"] and standard["actions"]
        assert standard["mechanism"]
        assert beginner["overview"] != standard["overview"]
    set_locale("en")


def test_config_mode_is_saved_without_losing_language(tmp_path, monkeypatch):
    import termdoctor.i18n as i18n
    monkeypatch.setattr(i18n, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(i18n, "CONFIG_FILE", tmp_path / "config.json")
    assert runner.invoke(app, ["set", "lang", "uk"]).exit_code == 0
    assert runner.invoke(app, ["set", "mode", "beginner"]).exit_code == 0
    settings = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert settings["language"] == "uk"
    assert settings["explanation_mode"] == "beginner"
    assert resolve_mode() == "beginner"
    assert runner.invoke(app, ["set", "mode", "expert"]).exit_code == 2
    assert json.loads((tmp_path / "config.json").read_text(encoding="utf-8")) == settings


def test_default_mode_stays_standard_for_existing_install(tmp_path, monkeypatch):
    import termdoctor.i18n as i18n
    monkeypatch.setattr(i18n, "CONFIG_FILE", tmp_path / "empty.json")
    monkeypatch.delenv("TERMDOCTOR_MODE", raising=False)
    assert resolve_mode() == "standard"


def test_ukrainian_beginner_cli_and_standard_json(tmp_path):
    script = tmp_path / "broken.py"
    script.write_text("print(username)\n", encoding="utf-8")
    env = _env(tmp_path, language="uk")
    beginner = subprocess.run([sys.executable, "-m", "termdoctor", "--mode", "beginner", str(script)],
                             text=True, encoding="utf-8", capture_output=True, env=env, timeout=15)
    assert beginner.returncode == 1
    assert "ЩО СТАЛОСЯ?" in beginner.stdout
    assert "ПОМІРКУЙ НАД ЦИМ" in beginner.stdout
    assert "Що перевірити" not in beginner.stdout
    assert "TermDoctor v0.4.1" in beginner.stdout
    standard = subprocess.run([sys.executable, "-m", "termdoctor", "--mode", "standard", "run", "--format", "json", "--", sys.executable, str(script)],
                             text=True, encoding="utf-8", capture_output=True, env=env, timeout=15)
    assert standard.returncode == 1
    payload = json.loads(standard.stdout)
    assert payload["diagnosis"]["interface_locale"] == "uk"
    assert payload["diagnosis"]["explanation_mode"] == "standard"
    assert payload["diagnosis"]["rule"]["educational"]["mechanism"]
    assert payload["diagnosis"]["rule"]["suggestions"]


def test_beginner_json_does_not_provide_direct_solutions(tmp_path):
    traceback = tmp_path / "error.txt"
    traceback.write_text('Traceback (most recent call last):\n  File "main.py", line 3, in <module>\n    print(username)\nNameError: name \'username\' is not defined\n')
    env = _env(tmp_path, language="en")
    out = subprocess.run([sys.executable, "-m", "termdoctor", "--mode", "beginner", "explain", str(traceback), "--format", "json"],
                         env=env, capture_output=True, text=True, encoding="utf-8", timeout=15)
    assert out.returncode == 0
    diagnosis = json.loads(out.stdout)
    assert diagnosis["explanation_mode"] == "beginner"
    assert diagnosis["rule"]["suggestions"] == []
    assert diagnosis["rule"]["possible_causes"] == []


def test_explicit_standard_mode_overrides_saved_beginner_mode(tmp_path):
    traceback = tmp_path / "error.txt"
    traceback.write_text(
        'Traceback (most recent call last):\n'
        '  File "main.py", line 1, in <module>\n'
        '    print(username)\n'
        "NameError: name 'username' is not defined\n",
        encoding="utf-8",
    )

    assert runner.invoke(app, ["set", "mode", "beginner"]).exit_code == 0

    standard = runner.invoke(
        app, ["--mode", "standard", "explain", str(traceback), "--format", "json"]
    )
    assert standard.exit_code == 0
    standard_data = json.loads(standard.output)
    assert standard_data["explanation_mode"] == "standard"
    assert standard_data["rule"]["suggestions"]

    beginner = runner.invoke(app, ["explain", str(traceback), "--format", "json"])
    assert beginner.exit_code == 0
    beginner_data = json.loads(beginner.output)
    assert beginner_data["explanation_mode"] == "beginner"
    assert beginner_data["rule"]["suggestions"] == []
