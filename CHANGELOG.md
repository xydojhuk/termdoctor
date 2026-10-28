# Changelog

All notable changes to TermDoctor are tracked here. Entries under **Unreleased** describe work that is not yet part of a published release.

## 0.4.0 - CLI foundation (2026-10-28)

### Added

- Short `td` command and `td file.py` / `termdoctor file.py` shortcuts.
- `set lang`, `set history`, and `config` commands; `change` is an alias for `set`.
- Streaming stdout/stderr with inherited stdin for interactive scripts.
- Optional execution timeout and handling of Ctrl+C.
- Interpreter-aware Python environment probe.
- Structured JSON diagnosis for future integrations (`--format json`).
- Multi-platform GitHub Actions test matrix and regression tests.

### Changed

- History is opt-in; existing history files are left untouched.
- Diagnosis title includes the TermDoctor version.
- Repository URLs point to `xydojhuk/termdoctor`.

### Fixed

- YAML boolean-like translation keys for common yes/no.

## 0.3.1 - Reliable Python Diagnosis and Localization (2026-07-17)

### Added

- Added English and Russian interface localization with `--lang en|ru`, aliases, environment-variable support, saved configuration, and English fallback.
- Added complete Russian translations for all 105 Python diagnosis rules.
- Added `--engine python` as the explicit engine selector while retaining the old command-level `--lang python` compatibility alias.
- Added `termdoctor config language [CODE]` and `--no-history` for sensitive runs.
- Added ANSI-colored traceback support, user-defined exception support, traceback frame collection, exception chains, and nearby source-code context.
- Added strict rule metadata: `match_any`, `match_all`, `exclude`, `full_error_types`, framework constraints, and priority.
- Added more precise rules for common `TypeError`, `ValueError`, `ImportError`, `AttributeError`, and Django command failures.
- Added Pydantic as its own detected ecosystem.
- Added support for versioned Python executables, Windows `.exe` paths, and common environment runners.
- Added optional dependencies, dependency groups, Poetry groups, Pipfile, VCS/direct references, and broader requirements-file discovery.
- Added source/standard-library/local-module checks for `ModuleNotFoundError`.
- Added secret redaction, output truncation, serialized and atomic history writes, private file permissions, corrupt-history backups, and combined diagnostic output.
- Added regression and localization tests.

### Changed

- Changed rule selection so specialized rules are used only when their evidence actually matches.
- Changed framework detection to require primary evidence, preventing Pydantic/Jinja2/Werkzeug from falsely identifying FastAPI or Flask.
- Changed command diagnosis to inspect both `stdout` and `stderr`.
- Changed Python project checks so absent optional frameworks are informational instead of warnings.
- Changed reports to inspect the original failure working directory instead of the current shell directory.
- Changed report and renderer output to use generic engine-provided diagnostic sections.
- Changed package version handling to use `termdoctor.__version__` as the single source of truth.
- Changed install hints to prefer the active interpreter via `python -m pip`.
- Updated documentation, architecture examples, privacy notes, and release commands for 0.3.1.

### Fixed

- Fixed Django `CommandError` being diagnosed as an Alembic failure.
- Fixed unmatched specialized rules falling back to the first rule with the same short exception name.
- Fixed `python3.13`, Windows `python.exe`, and Windows `pytest.exe` command detection.
- Fixed ANSI escape codes and custom exception names preventing traceback parsing.
- Fixed unreachable rules for dotted or non-`*Error` exception names.
- Fixed false FastAPI detection from Pydantic alone.
- Fixed local and standard-library imports receiving inappropriate `pip install` suggestions.
- Fixed reports generated from history using unrelated project metadata.
- Fixed stale rule paths and outdated project structure in user-facing output.
- Fixed concurrent history updates losing entries.

## 0.3.0 - Language Engine Architecture

### Added

- Added language engine architecture.
- Added `BaseEngine` abstraction.
- Added `EngineDiagnosis` model.
- Added `PythonEngine`.
- Added `LanguageDetector`.
- Added default engine registry.
- Added language-specific Python rules at `src/termdoctor/engines/python/rules.yml`.
- Added `termdoctor languages` command.
- Added `--lang python` option for `explain`, `paste`, and `report`.
- Added engine tests.
- Added CLI tests for language engine commands.

### Changed

- Moved Python rule loading into `PythonEngine`.
- Updated CLI diagnosis flow to use language detection.
- Updated Markdown reports to use engine diagnosis.
- Updated `matcher.py` and `rules_loader.py` as compatibility wrappers around `PythonEngine`.
- Updated package data to include language-specific rules.
- Updated README for engine-based architecture.

### Removed

- Removed old global `src/termdoctor/rules/python_errors.yml` rule location.

## 0.2.3 - Python Framework Diagnosis

### Added

- Added framework detection for Django, FastAPI, Flask, Pydantic, SQLAlchemy, Alembic, pytest, aiogram, and pyTelegramBotAPI.
- Added framework-aware diagnosis context.
- Added framework-specific Python rules.
- Added framework traceback examples.
- Added framework tests.

## 0.2.2 - Reports & Better Python Diagnosis

### Added

- Added Markdown report generation.
- Added `termdoctor report` command.
- Added more Python error rules.
- Added more report tests and examples.

## 0.2.1 - Environment Polish

### Added

- Added project root detection.
- Added OS-aware virtual environment activation hints.
- Added nested requirements parsing.
- Added more package hints.

## 0.2.0 - Python Environment Awareness

### Added

- Added `termdoctor env`.
- Added `termdoctor doctor python`.
- Added Python environment and dependency awareness.
- Added smarter `ModuleNotFoundError` diagnosis.

## 0.1.1 - Stability Patch

### Added

- Added safer command execution format with `termdoctor run -- ...`.
- Improved traceback parsing and history output.

## 0.1.0 - Initial Release

### Added

- Initial Python-only CLI.
- Rule-based Python error diagnosis.
- Basic examples and tests.
