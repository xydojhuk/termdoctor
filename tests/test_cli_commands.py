from typer.testing import CliRunner

from termdoctor import __version__
from termdoctor.cli import app


runner = CliRunner()


def test_version_command():
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "TermDoctor" in result.output
    assert __version__ in result.output.replace("\x1b[1;36m", "").replace("\x1b[0m", "")


def test_env_command_runs():
    result = runner.invoke(app, ["env"])

    assert result.exit_code == 0
    assert "Python environment" in result.output


def test_doctor_python_command_runs():
    result = runner.invoke(app, ["doctor", "python"])

    assert result.exit_code == 0
    assert "TermDoctor Python doctor" in result.output

def test_report_command_from_file(tmp_path):
    traceback_file = tmp_path / "error.txt"
    traceback_file.write_text(
        """
        Traceback (most recent call last):
        File "main.py", line 1, in <module>
            print(username)
        NameError: name 'username' is not defined
        """,
        encoding="utf-8",
    )

    result = runner.invoke(app, ["report", str(traceback_file)])

    assert result.exit_code == 0
    assert "TermDoctor Report" in result.output
    assert "NameError" in result.output


def test_report_command_writes_output_file(tmp_path):
    traceback_file = tmp_path / "error.txt"
    output_file = tmp_path / "report.md"
    traceback_file.write_text(
        """
        Traceback (most recent call last):
        File "main.py", line 1, in <module>
            print(username)
        NameError: name 'username' is not defined
        """,
        encoding="utf-8",
    )

    result = runner.invoke(app, ["report", str(traceback_file), "--output", str(output_file)])

    assert result.exit_code == 0
    assert output_file.exists()
    assert "NameError" in output_file.read_text(encoding="utf-8")

def test_languages_command_runs():
    result = runner.invoke(app, ["languages"])

    assert result.exit_code == 0
    assert "Supported language engines" in result.output
    assert "Python" in result.output


def test_explain_with_lang_python(tmp_path):
    traceback_file = tmp_path / "error.txt"
    traceback_file.write_text(
        """
        Traceback (most recent call last):
        File "main.py", line 1, in <module>
            print(username)
        NameError: name 'username' is not defined
        """,
        encoding="utf-8",
    )

    result = runner.invoke(app, ["explain", str(traceback_file), "--lang", "python"])

    assert result.exit_code == 0
    assert "TermDoctor v0.4.1 · NameError" in result.output
    assert "NameError" in result.output