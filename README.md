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
  <a href="https://github.com/xydojhuk/termdoctor/actions/workflows/tests.yml"><img alt="Tests" src="https://github.com/xydojhuk/termdoctor/actions/workflows/tests.yml/badge.svg"></a>
</p>

## Features

- **Short commands:** `td main.py` or `termdoctor main.py` instead of wrapping every Python call manually.
- **Python traceback diagnosis:** identify exceptions, show source context when available, and suggest possible causes and fixes.
- **Python project context:** inspect interpreters, virtual environments, dependency files, and project structure.
- **Framework-aware rules:** Django, FastAPI, Flask, Pydantic, SQLAlchemy, Alembic, pytest, aiogram, and pyTelegramBotAPI.
- **Three interface languages:** English (`en`), Russian (`ru`), and Ukrainian (`uk`).
- **Two explanation modes:** Beginner provides guided questions without direct fixes; Standard describes Python behavior, possible causes, and concrete checks.
- **Local operation:** no account, cloud API, or network connection needed for diagnostics.
- **Privacy-conscious defaults:** failure history is **off** unless you turn it on.

TermDoctor currently diagnoses **Python** errors. It is a diagnostic helper, not an automatic code fixer; suggestions may require verification against your project.

## Installation

**Requirement:** Python 3.10 or newer. Both `td` and `termdoctor` are installed.

Recommended installation with [pipx](https://pipx.pypa.io/):

```bash
pipx install git+https://github.com/xydojhuk/termdoctor.git@v0.4.1
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

## Usage

### Run a Python file

```bash
td main.py
termdoctor main.py
td "my script.py" "argument with spaces"
```

TermDoctor runs the script using an active virtual environment when available, otherwise a detected project virtual environment or a Python interpreter from `PATH`. It shows normal program output and, if Python fails, prints a diagnosis. Interactive scripts using `input()` are supported.

### Language and explanation mode

```bash
td set lang ru
td set lang uk
td set lang en
td set mode beginner
td set mode standard
td config
```

To change settings for one command only:

```bash
td --lang uk --mode beginner main.py
td --lang en --mode standard main.py
```

**Beginner** explains the error in plain language, points to its location, and asks a diagnostic question. **Standard** provides technical explanations, relevant causes, and specific checks. Standard remains the default for existing installations. `td change` is an alias for `td set`.

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

`--format json` returns structured diagnostic data, including the selected explanation mode. JSON run mode captures output and is not interactive.

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

## Tech stack

**Python 3.10+**, [Typer](https://typer.tiangolo.com/), [Rich](https://rich.readthedocs.io/), and [PyYAML](https://pyyaml.org/). TermDoctor uses a rule-based Python diagnostic engine; no AI service is required.

## Contributing

Bug reports and focused pull requests are welcome. Please include your Python version, operating system, the command you ran, expected vs. actual behavior, and a minimal reproducible example **without secrets**. Run the tests before opening a pull request.

For ordinary bugs and feature requests, use [GitHub Issues](https://github.com/xydojhuk/termdoctor/issues). For security issues, follow the private-reporting guidance below instead.

## Security

Read [SECURITY.md](SECURITY.md) before reporting a potential vulnerability. Do **not** publish exploits, credentials, or sensitive tracebacks in public issues.

## License

TermDoctor is available under the [MIT License](LICENSE).
