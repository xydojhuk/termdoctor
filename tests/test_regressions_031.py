from pathlib import Path

from typer.testing import CliRunner

from termdoctor.cli import app
from termdoctor.core.history import sanitize_output
from termdoctor.engines.python.engine import PythonEngine
from termdoctor.engines.python.environment import build_module_diagnosis_context, diagnose_python_project
from termdoctor.engines.python.frameworks import detect_frameworks
from termdoctor.engines.python.parser import parse_python_error
from termdoctor.models import CommandResult, ParsedError


runner = CliRunner()


def test_python_engine_detects_versioned_and_windows_commands():
    engine = PythonEngine()

    assert engine.can_handle_command("python3.13 app.py") is True
    assert engine.can_handle_command(r'C:\Python313\python.exe app.py') is True
    assert engine.can_handle_command([r"C:\project\.venv\Scripts\pytest.exe", "-q"]) is True
    assert engine.can_handle_command("pdm run python3.12 app.py") is True


def test_parser_strips_ansi_and_accepts_custom_exception():
    text = (
        "\x1b[31mTraceback (most recent call last):\x1b[0m\n"
        '  File "main.py", line 4, in <module>\n'
        "    raise Boom('broken')\n"
        "\x1b[31mBoom: broken\x1b[0m"
    )

    parsed = parse_python_error(text)

    assert parsed is not None
    assert parsed.error_type == "Boom"
    assert parsed.message == "broken"
    assert parsed.file_path == "main.py"
    assert parsed.line_number == 4
    assert "\x1b" not in parsed.raw_text


def test_parser_does_not_add_lowercase_source_line_to_exception_chain():
    parsed = parse_python_error(
        """
        Traceback (most recent call last):
          File "main.py", line 2, in <module>
            username
        NameError: name 'username' is not defined
        """
    )

    assert parsed is not None
    assert parsed.exception_chain == ["NameError"]


def test_django_command_error_never_uses_alembic_rule():
    parsed = ParsedError(
        error_type="CommandError",
        message="Unknown command: foo",
        raw_text="django.core.management.base.CommandError: Unknown command: foo",
        full_error_type="django.core.management.base.CommandError",
        extracted={"full_error_type": "django.core.management.base.CommandError"},
    )

    rule = PythonEngine().find_rule(parsed, locale="en")

    assert rule is not None
    assert rule.id == "django_command_error"


def test_unrelated_command_error_has_no_false_alembic_diagnosis():
    parsed = ParsedError(
        error_type="CommandError",
        message="custom command failed",
        raw_text="mytool.CommandError: custom command failed",
        full_error_type="mytool.CommandError",
    )

    assert PythonEngine().find_rule(parsed, locale="en") is None


def test_pydantic_dependency_does_not_detect_fastapi(tmp_path):
    result = detect_frameworks(tmp_path, ["pydantic"])

    assert result.is_detected("Pydantic") is True
    assert result.is_detected("FastAPI") is False


def test_doctor_missing_frameworks_are_info_not_warnings(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='demo'\ndependencies=[]\n",
        encoding="utf-8",
    )

    result = diagnose_python_project(tmp_path)
    framework_check = next(check for check in result.checks if check.label_key == "doctor.no_frameworks")

    assert framework_check.status == "info"
    assert not any("Django" in warning.key for warning in result.warnings)


def test_module_context_recognizes_local_module(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")

    context = build_module_diagnosis_context("app", tmp_path)

    assert context.local_module_path is not None
    assert context.should_suggest_install is False


def test_module_context_recognizes_standard_library(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")

    context = build_module_diagnosis_context("json.tool", tmp_path)

    assert context.top_level_module == "json"
    assert context.is_standard_library is True
    assert context.should_suggest_install is False


def test_command_result_combines_stdout_and_stderr():
    result = CommandResult("demo", "/tmp", 1, "warning on stdout", "NameError: bad", 0.1)

    assert "warning on stdout" in result.diagnostic_text
    assert "NameError: bad" in result.diagnostic_text


def test_history_sanitizes_secrets_and_long_output():
    raw = "Authorization: Bearer abc123\nPASSWORD=supersecret\n" + "x" * 100

    sanitized = sanitize_output(raw, limit=50)

    assert "abc123" not in sanitized
    assert "supersecret" not in sanitized
    assert "REDACTED" in sanitized
    assert "truncated" in sanitized


def test_cli_global_russian_language(tmp_path):
    traceback_file = tmp_path / "error.txt"
    traceback_file.write_text(
        "Traceback (most recent call last):\n"
        '  File "main.py", line 1, in <module>\n'
        "    print(username)\n"
        "NameError: name 'username' is not defined\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["--lang", "rus", "explain", str(traceback_file)])

    assert result.exit_code == 0
    assert "TermDoctor v0.4.1 · NameError" in result.output
    assert "Python встретил имя" in result.output


def test_run_no_history_option_is_accepted():
    result = runner.invoke(
        app,
        ["run", "--no-history", "--", "python", "-c", "raise NameError('demo')"],
    )

    assert result.exit_code != 0
    assert "NameError" in result.output
