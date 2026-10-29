"""Dispatch convenience `td file.py` without changing the Typer command tree."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from termdoctor.core.project import find_project_root


def choose_python(script: str, *, cwd: Path | None = None) -> str:
    """Prefer an active venv, then the project's .venv, then PATH.

    Never use sys.executable as a default: under pipx that is TermDoctor's
    private interpreter and need not contain the student's dependencies.
    """
    base = (cwd or Path.cwd()).resolve()
    active = os.environ.get("VIRTUAL_ENV")
    if active:
        candidate = Path(active) / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if candidate.is_file():
            return str(candidate)
    project_root = find_project_root(base)
    script_path = (base / script).resolve()
    if project_root == base and script_path.is_file():
        project_root = find_project_root(script_path.parent)
    for folder in (".venv", "venv"):
        candidate = project_root / folder / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if candidate.is_file():
            return str(candidate)
    for name in (("python", "py", "python3") if os.name == "nt" else ("python3", "python")):
        path = shutil.which(name)
        if path:
            return path
    raise RuntimeError("Python interpreter not found. Install Python or select an environment.")


def expand_script_shortcut(argv: list[str]) -> list[str]:
    """Transform `td [--lang ru] [--mode beginner] script.py [args]` into an explicit run.

    Do not reinterpret built-in subcommands or other arbitrary shell commands.
    """
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg in {"--lang", "--mode"}:
            index += 2
            continue
        if arg.startswith(("--lang=", "--mode=")):
            index += 1
            continue
        if arg.startswith("-"):
            return argv
        if arg.lower().endswith((".py", ".pyw")):
            interpreter = choose_python(arg)
            return argv[:index] + ["run", "--", interpreter, *argv[index:]]
        return argv
    return argv
