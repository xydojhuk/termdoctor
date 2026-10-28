from __future__ import annotations

import re
import shlex
from importlib import resources
from pathlib import Path, PurePosixPath, PureWindowsPath

import yaml

from termdoctor.engines.base import BaseEngine, EngineDiagnosis
from termdoctor.engines.python.environment import build_module_diagnosis_context, get_python_environment
from termdoctor.engines.python.frameworks import build_framework_diagnosis_context, detect_framework_from_error
from termdoctor.engines.python.parser import attach_source_context, parse_python_error
from termdoctor.i18n import get_locale, normalize_locale
from termdoctor.models import (
    CommandResult,
    DiagnosticField,
    DiagnosticMessage,
    DiagnosticSection,
    ErrorRule,
    ParsedError,
)


PYTHON_EXECUTABLE_PATTERN = re.compile(r"^(?:python(?:\d+(?:\.\d+)*)?|py)$", re.IGNORECASE)
DIRECT_COMMANDS = {
    "pytest",
    "django-admin",
    "uvicorn",
    "gunicorn",
    "flask",
    "alembic",
}
RUN_WRAPPERS = {"uv", "poetry", "pipenv", "hatch", "pdm", "rye"}


class PythonEngine(BaseEngine):
    language = "python"
    display_name = "Python"

    text_markers = (
        "Traceback (most recent call last):",
        "File \"",
        "File '",
        "Error:",
        "Exception:",
        "django.",
        "fastapi.",
        "pydantic.",
        "sqlalchemy.",
        "alembic.",
        "aiogram.",
        "telebot.",
        "_pytest.",
    )

    def can_handle_command(self, command: str | list[str]) -> bool:
        parts = command_to_parts(command)
        if not parts:
            return False

        first = normalize_executable(parts[0])
        if is_python_executable(first) or first in DIRECT_COMMANDS:
            return True

        if first in RUN_WRAPPERS:
            lowered = [normalize_executable(part) for part in parts[1:]]
            if "run" in lowered or first == "uv":
                return any(is_python_executable(part) or part in DIRECT_COMMANDS for part in lowered)

        if first == "py":
            return True
        return False

    def can_handle_text(self, text: str) -> bool:
        if any(marker in text for marker in self.text_markers):
            return self.parse_error(text) is not None
        return False

    def parse_error(self, text: str) -> ParsedError | None:
        parsed_error = parse_python_error(text)
        if parsed_error:
            parsed_error.language = self.language
        return parsed_error

    def load_rules(self, locale: str | None = None) -> list[ErrorRule]:
        rules_file = resources.files("termdoctor").joinpath("engines/python/rules.yml")
        with rules_file.open("r", encoding="utf-8") as file:
            raw_rules = yaml.safe_load(file) or []

        selected_locale = normalize_locale(locale) if locale else get_locale()
        translations = self._load_rule_translations(selected_locale)
        rules: list[ErrorRule] = []
        for raw_rule in raw_rules:
            merged = dict(raw_rule)
            translated = translations.get(str(raw_rule.get("id", "")), {})
            if isinstance(translated, dict):
                for key in ("title", "explanation", "causes", "fixes", "examples"):
                    if key in translated:
                        merged[key] = translated[key]
            rules.append(ErrorRule.from_dict(merged))
        return rules

    def _load_rule_translations(self, locale: str) -> dict[str, dict]:
        if locale == "en":
            return {}
        translation_file = resources.files("termdoctor").joinpath(
            f"engines/python/rules.{locale}.yml"
        )
        try:
            with translation_file.open("r", encoding="utf-8") as file:
                data = yaml.safe_load(file) or {}
        except FileNotFoundError:
            return {}
        if isinstance(data, list):
            return {str(item.get("id", "")): item for item in data if isinstance(item, dict)}
        return data if isinstance(data, dict) else {}

    def find_rule(self, parsed_error: ParsedError, locale: str | None = None) -> ErrorRule | None:
        candidates = [
            rule for rule in self.load_rules(locale) if rule.error == parsed_error.error_type
        ]
        if not candidates:
            return None

        searchable_text = build_searchable_text(parsed_error)
        matched_framework = detect_framework_from_error(parsed_error)
        scored: list[tuple[int, ErrorRule]] = []
        fallbacks: list[ErrorRule] = []
        for rule in candidates:
            if rule.is_fallback:
                fallbacks.append(rule)
                continue
            score = score_rule(rule, parsed_error, searchable_text, matched_framework)
            if score is not None:
                scored.append((score, rule))

        if scored:
            scored.sort(key=lambda item: (item[0], item[1].priority), reverse=True)
            return scored[0][1]
        if fallbacks:
            return max(fallbacks, key=lambda rule: rule.priority)
        return None

    def diagnose(
        self,
        text: str,
        command_result: CommandResult | None = None,
        cwd: Path | None = None,
        locale: str | None = None,
        python_executable: str | None = None,
    ) -> EngineDiagnosis | None:
        parsed_error = self.parse_error(text)
        if parsed_error is None:
            return None

        diagnosis_cwd = cwd or (Path(command_result.cwd) if command_result else Path.cwd())
        attach_source_context(parsed_error, diagnosis_cwd)
        environment = get_python_environment(diagnosis_cwd, python_executable)
        rule = self.find_rule(parsed_error, locale=locale)
        module_context = None
        if parsed_error.error_type == "ModuleNotFoundError":
            module_name = parsed_error.extracted.get("module")
            if module_name:
                module_context = build_module_diagnosis_context(module_name, diagnosis_cwd, python_executable)

        framework_context = build_framework_diagnosis_context(
            parsed_error,
            environment.framework_info,
        )
        sections = build_diagnostic_sections(module_context, framework_context)
        return EngineDiagnosis(
            language=self.language,
            display_name=self.display_name,
            parsed_error=parsed_error,
            rule=rule,
            command_result=command_result,
            sections=sections,
            environment=environment,
            module_context=module_context,
            framework_context=framework_context,
        )


def command_to_parts(command: str | list[str]) -> list[str]:
    if isinstance(command, list):
        return [str(part) for part in command]
    try:
        return shlex.split(command, posix=False if "\\" in command else True)
    except ValueError:
        return command.split()


def normalize_executable(value: str) -> str:
    cleaned = value.strip().strip('"\'')
    windows_name = PureWindowsPath(cleaned).name
    posix_name = PurePosixPath(windows_name).name
    lowered = posix_name.lower()
    if lowered.endswith(".exe"):
        lowered = lowered[:-4]
    return lowered


def is_python_executable(value: str) -> bool:
    return bool(PYTHON_EXECUTABLE_PATTERN.match(value))


def build_searchable_text(parsed_error: ParsedError) -> str:
    return "\n".join(
        [
            parsed_error.error_type,
            parsed_error.message,
            parsed_error.raw_text,
            parsed_error.full_error_type or parsed_error.extracted.get("full_error_type", ""),
        ]
    ).lower()


def score_rule(
    rule: ErrorRule,
    parsed_error: ParsedError,
    searchable_text: str,
    matched_framework: str | None,
) -> int | None:
    if any(phrase.lower() in searchable_text for phrase in rule.exclude):
        return None

    score = rule.priority
    full_error_type = (parsed_error.full_error_type or parsed_error.extracted.get("full_error_type", "")).lower()
    if rule.full_error_types:
        normalized_types = [item.lower() for item in rule.full_error_types]
        if not any(
            full_error_type == item or full_error_type.endswith(f".{item}")
            for item in normalized_types
        ):
            return None
        score += 100

    if rule.frameworks:
        if not matched_framework or matched_framework.lower() not in {
            framework.lower() for framework in rule.frameworks
        }:
            return None
        score += 50

    if rule.match_all:
        if not all(phrase.lower() in searchable_text for phrase in rule.match_all):
            return None
        score += 20 * len(rule.match_all)

    if rule.match_any:
        matches = [phrase for phrase in rule.match_any if phrase.lower() in searchable_text]
        if not matches:
            return None
        score += 10 * len(matches) + max(len(phrase) for phrase in matches)

    return score


def build_diagnostic_sections(module_context, framework_context) -> list[DiagnosticSection]:
    sections: list[DiagnosticSection] = []
    if framework_context:
        sections.append(
            DiagnosticSection(
                title_key="framework.title",
                fields=[
                    DiagnosticField("framework.matched", framework_context.matched_framework or "-"),
                    DiagnosticField(
                        "framework.detected",
                        ", ".join(item.name for item in framework_context.detected_frameworks) or "-",
                    ),
                    DiagnosticField("framework.evidence", ", ".join(framework_context.evidence) or "-"),
                ],
            )
        )

    if module_context:
        fields = [
            DiagnosticField("module.missing_import", module_context.module_name),
            DiagnosticField("module.top_level_import", module_context.top_level_module),
            DiagnosticField("module.suggested_package", module_context.package_name),
            DiagnosticField("module.current_directory", module_context.current_dir),
            DiagnosticField("module.project_root", module_context.project_root),
            DiagnosticField("module.python_executable", module_context.python_executable),
            DiagnosticField("module.active_venv_path", module_context.active_venv_path or "-"),
            DiagnosticField("module.project_venv", module_context.project_venv_path or "-"),
            DiagnosticField("module.activation_command", module_context.activation_command or "-"),
            DiagnosticField("module.local_module", module_context.local_module_path or "-"),
        ]
        suggestions: list[DiagnosticMessage] = []
        if module_context.is_standard_library:
            suggestions.append(DiagnosticMessage("module.stdlib_missing"))
        elif module_context.local_module_path:
            suggestions.append(
                DiagnosticMessage("module.local_found", {"path": module_context.local_module_path})
            )
        else:
            if module_context.package_hint:
                suggestions.append(
                    DiagnosticMessage(
                        "module.install_hint",
                        {
                            "python": module_context.python_executable,
                            "package": module_context.package_hint,
                        },
                    )
                )
            if module_context.project_venv_path and not module_context.venv_active:
                if module_context.activation_command:
                    suggestions.append(
                        DiagnosticMessage("module.activate", {"command": module_context.activation_command})
                    )
                else:
                    suggestions.append(DiagnosticMessage("module.activate_generic"))
            if module_context.in_requirements:
                suggestions.append(DiagnosticMessage("module.install_requirements"))
            if module_context.in_pyproject:
                suggestions.append(
                    DiagnosticMessage(
                        "module.install_pyproject",
                        {"python": module_context.python_executable},
                    )
                )
            if not module_context.in_requirements and not module_context.in_pyproject:
                suggestions.append(
                    DiagnosticMessage(
                        "module.third_party",
                        {
                            "python": module_context.python_executable,
                            "package": module_context.package_name,
                        },
                    )
                )
        sections.append(DiagnosticSection("module.title", fields, suggestions))
    return sections
