<p align="center">
  <img src="assets/banner.png" alt="TermDoctor" width="100%">
</p>

<h1 align="center">TermDoctor</h1>

<p align="center">
  <strong>Understand Python errors directly in your terminal.</strong><br>
  A local, multilingual debugging assistant that explains what went wrong and helps you find the cause.
</p>

<p align="center">
  <a href="https://github.com/xydojhuk/termdoctor/releases"><img alt="Latest published release" src="https://img.shields.io/github/v/release/xydojhuk/termdoctor?include_prereleases&style=flat-square"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/github/license/xydojhuk/termdoctor?style=flat-square"></a>
</p>

<!-- Add the CI badge after .github/workflows/tests.yml is pushed and has run successfully:
<a href="https://github.com/xydojhuk/termdoctor/actions/workflows/tests.yml"><img alt="Tests" src="https://github.com/xydojhuk/termdoctor/actions/workflows/tests.yml/badge.svg"></a>
-->

## Features

- **Short commands:** `td main.py` or `termdoctor main.py` instead of wrapping every Python call manually.
- **Python traceback diagnosis:** identify exceptions, show source context when available, and suggest possible causes and fixes.
- **Python project context:** inspect interpreters, virtual environments, dependency files, and project structure.
- **Framework-aware rules:** Django, FastAPI, Flask, Pydantic, SQLAlchemy, Alembic, pytest, aiogram, and pyTelegramBotAPI.
- **Two interface languages:** English (`en`) and Russian (`ru`).
- **Local operation:** no account, cloud API, or network connection needed for diagnostics.
- **Privacy-conscious defaults:** failure history is **off** unless you turn it on.

TermDoctor currently diagnoses **Python** errors. It is a diagnostic helper, not an automatic code fixer; suggestions may require verification against your project.

## Screenshots

_Screenshots will be added after the CLI examples are captured._

<!-- Screenshot slots: replace this note with real images when available.
     Store captures in assets/screenshots/ and use descriptive alt text.
     Example paths: assets/screenshots/diagnosis-en.png, assets/screenshots/diagnosis-ru.png.
     Avoid exposing API keys, private file paths, or other secrets in screenshots.
-->

## Installation

**Requirement:** Python 3.10 or newer. The `td` command is installed together with `termdoctor`.

Recommended installation with [pipx](https://pipx.pypa.io/):

```bash
pipx install git+https://github.com/xydojhuk/termdoctor.git
```

Check the installed command:

```bash
td --version
td --help
```

You can also install from a local checkout (including a development branch):

```bash
git clone https://github.com/xydojhuk/termdoctor.git
cd termdoctor
pipx install .
```

> **Releases:** the badge above shows the latest published GitHub Release. Installation from the default branch uses its current source, which may differ from the most recent tagged release.

## Usage

### Run a Python file

```bash
td main.py
termdoctor main.py
td "my script.py" "argument with spaces"
```

TermDoctor runs the script using an active virtual environment when available, otherwise a detected project virtual environment or a Python interpreter from `PATH`. It shows normal program output and, if Python fails, prints a diagnosis. Interactive scripts using `input()` are supported.

### Choose an explanation language

```bash
td set lang ru       # Save Russian
td set lang en       # Save English
td config            # Show current settings
td --lang ru main.py # Use Russian for this run only
```

`td change lang ru` is also accepted as an alias for `td set lang ru`.

### Inspect an error or environment

```bash
td explain error.txt
td doctor python
td env
```

### Run a command explicitly

```bash
td run -- python -m pytest
td run --timeout 10 -- python main.py
```

The original `termdoctor run -- python main.py` syntax remains available for compatibility.

<details>
<summary>Additional CLI commands and machine-readable output</summary>

```bash
td explain error.txt --format json
td run --format json -- python main.py
td report error.txt -o report.md
td paste
td history
td clear
```

JSON output is intended for integrations, not regular terminal reading. The JSON run mode captures output and does not provide the same interactive behavior as the default text mode.

To save failed runs explicitly:

```bash
td set history on
td set history off
```

Saved history is stored locally in `~/.termdoctor/history.json` (or the current user's home directory equivalent). Upgrading does **not** delete existing history. Redaction is best-effort, not a guarantee; avoid turning on history for sensitive commands.

</details>

## Development and testing

Clone the repository, create a virtual environment, and install development dependencies:

```bash
git clone https://github.com/xydojhuk/termdoctor.git
cd termdoctor
python -m venv .venv
```

Activate the environment for your shell:

```bash
# Linux / macOS (bash, zsh)
source .venv/bin/activate
# Linux / macOS (fish): source .venv/bin/activate.fish
# Windows PowerShell: .venv\Scripts\Activate.ps1
```

Then run:

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python -m build --wheel
```

A GitHub Actions workflow is provided in `.github/workflows/tests.yml` for Linux, Windows, and macOS (Python 3.10–3.13). Passing CI on one set of dependency versions does not prove compatibility with every older version permitted by dependency ranges.

## Tech stack

**Python 3.10+**, [Typer](https://typer.tiangolo.com/), [Rich](https://rich.readthedocs.io/), and [PyYAML](https://pyyaml.org/). TermDoctor uses a rule-based Python diagnostic engine; no AI service is required.

## Contributing

Bug reports and focused pull requests are welcome. Please include your Python version, operating system, the command you ran, expected vs. actual behavior, and a minimal reproducible example **without secrets**. Run the tests before opening a pull request.

For ordinary bugs and feature requests, use [GitHub Issues](https://github.com/xydojhuk/termdoctor/issues). For security issues, follow the private-reporting guidance below instead.

## Security

Read [SECURITY.md](SECURITY.md) before reporting a potential vulnerability. Do **not** publish exploits, credentials, or sensitive tracebacks in public issues.

## License

TermDoctor is available under the [MIT License](LICENSE).
