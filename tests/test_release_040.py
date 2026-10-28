"""Integration and regression tests for the v0.4.0 CLI foundation."""
import json
import os
import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

from termdoctor.cli import app
from termdoctor.core.runner import run_shell_command
from termdoctor.core.shortcuts import expand_script_shortcut
from termdoctor.engines.python.environment import get_python_environment
from termdoctor.i18n import tr

ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


def sandbox_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update({"HOME": str(tmp_path), "USERPROFILE": str(tmp_path),
                "PYTHONPATH": str(ROOT / "src"), "TERMDOCTOR_LANG": "en"})
    return env


def test_shortcut_expands_paths_and_flags(monkeypatch):
    monkeypatch.setattr("termdoctor.core.shortcuts.choose_python", lambda s: "/some/python")
    assert expand_script_shortcut(["hello world.py", "--name", "Alice"]) == [
        "run", "--", "/some/python", "hello world.py", "--name", "Alice"
    ]
    assert expand_script_shortcut(["--lang", "ru", "test.py"]) == [
        "--lang", "ru", "run", "--", "/some/python", "test.py"
    ]
    assert expand_script_shortcut(["explain", "error.txt"]) == ["explain", "error.txt"]


def test_shortcut_runs_interactive_program(tmp_path):
    script = tmp_path / "ask with space.py"
    script.write_text('who = input("Your name? ")\nprint("Hello, " + who)\n', encoding="utf-8")
    proc = subprocess.run([sys.executable, "-m", "termdoctor", str(script)],
                          input="Ada\n", capture_output=True, text=True,
                          env=sandbox_env(tmp_path), timeout=12)
    assert proc.returncode == 0
    assert "Your name? " in proc.stdout
    assert "Hello, Ada" in proc.stdout


def test_shortcut_reports_error_and_preserves_exit_code(tmp_path):
    script = tmp_path / "broken.py"
    script.write_text("print(unknown_name)\n", encoding="utf-8")
    proc = subprocess.run([sys.executable, "-m", "termdoctor", str(script)],
                          capture_output=True, text=True, env=sandbox_env(tmp_path), timeout=12)
    assert proc.returncode == 1
    assert "TermDoctor v0.4.0" in proc.stdout
    assert "NameError" in proc.stdout
    assert not (tmp_path / ".termdoctor" / "history.json").exists()


def test_localization_yes_no_keys_fixed():
    assert tr("common.yes", locale="ru") == "да"
    assert tr("common.no", locale="en") == "no"


def test_config_save_lang_and_history(tmp_path, monkeypatch):
    import termdoctor.i18n as i18n
    monkeypatch.setattr(i18n, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(i18n, "CONFIG_FILE", tmp_path / "config.json")
    assert runner.invoke(app, ["set", "lang", "ru"]).exit_code == 0
    assert runner.invoke(app, ["set", "history", "on"]).exit_code == 0
    assert runner.invoke(app, ["change", "history", "off"]).exit_code == 0
    assert json.loads((tmp_path / "config.json").read_text())["history_enabled"] is False
    assert i18n.history_enabled() is False
    assert runner.invoke(app, ["config"]).exit_code == 0


def test_json_explain_is_valid_machine_readable(tmp_path):
    source = tmp_path / "error.txt"
    source.write_text('Traceback (most recent call last):\n  File "main.py", line 1, in <module>\n'
                      "    print(username)\nNameError: name 'username' is not defined\n")
    result = runner.invoke(app, ["explain", str(source), "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["schema_version"] == 1
    assert data["error"]["type"] == "NameError"
    assert "raw_traceback" not in data
    assert data["rule"]["suggestions"]


def test_json_run_does_not_mix_program_output(tmp_path):
    script = tmp_path / "broken.py"
    script.write_text('print("ordinary output")\nraise ValueError("fail")\n')
    proc = subprocess.run([sys.executable, "-m", "termdoctor", "run", "--format", "json", "--", sys.executable, str(script)],
                          capture_output=True, text=True, env=sandbox_env(tmp_path), timeout=12)
    assert proc.returncode == 1
    obj = json.loads(proc.stdout)
    assert obj["diagnosis"]["error"]["type"] == "ValueError"


def test_runner_timeout(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = run_shell_command([sys.executable, "-c", "import time;time.sleep(3)"], timeout=0.1)
    assert result.exit_code == 124
    assert "timed out" in result.stderr


def test_probe_target_python(tmp_path):
    env = get_python_environment(tmp_path, python_executable=sys.executable)
    assert Path(env.python_executable).resolve() == Path(sys.executable).resolve()
    assert env.python_version.startswith(str(sys.version_info.major))


def test_shortcut_preserves_python_argument_with_spaces(tmp_path):
    script = tmp_path / "showargs.py"
    script.write_text("import sys; print(repr(sys.argv[1:]))\n")
    proc = subprocess.run([sys.executable, "-m", "termdoctor", str(script), "a b", "--flag"],
                          capture_output=True, text=True, env=sandbox_env(tmp_path), timeout=12)
    assert proc.returncode == 0
    assert "['a b', '--flag']" in proc.stdout
