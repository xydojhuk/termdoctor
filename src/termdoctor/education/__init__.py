"""Two distinct educational presentations of the same verified diagnosis.

Beginner asks a diagnostic question without prescribing a code change.
Standard explains the exception mechanism and gives concrete checks.
Neither mode changes rule matching or the original exception text.
"""
from __future__ import annotations

from contextvars import ContextVar
from importlib import resources
from typing import TYPE_CHECKING

import yaml

from termdoctor.i18n import get_locale, tr

if TYPE_CHECKING:
    from termdoctor.models import ErrorRule, ParsedError

_active_mode: ContextVar[str] = ContextVar("termdoctor_explanation_mode", default="standard")
_question_cache: dict[str, dict[str, str]] = {}
_mechanism_cache: dict[str, dict[str, str]] = {}
_summary_cache: dict[str, dict[str, str]] = {}


def set_active_mode(mode: str) -> None:
    _active_mode.set(mode)


def get_active_mode() -> str:
    return _active_mode.get()


def _questions(locale: str) -> dict[str, str]:
    if locale not in _question_cache:
        resource = resources.files("termdoctor").joinpath(f"education/questions.{locale}.yml")
        with resource.open(encoding="utf-8") as stream:
            data = yaml.safe_load(stream) or {}
        _question_cache[locale] = data
    return _question_cache[locale]


def _summaries(locale: str) -> dict[str, str]:
    if locale not in _summary_cache:
        with resources.files("termdoctor").joinpath(f"education/summaries.{locale}.yml").open(encoding="utf-8") as stream:
            _summary_cache[locale] = yaml.safe_load(stream) or {}
    return _summary_cache[locale]


def _mechanisms(locale: str) -> dict[str, str]:
    if locale not in _mechanism_cache:
        with resources.files("termdoctor").joinpath(f"education/mechanisms.{locale}.yml").open(encoding="utf-8") as stream:
            _mechanism_cache[locale] = yaml.safe_load(stream) or {}
    return _mechanism_cache[locale]


def _apply(template: str, error: ParsedError) -> str:
    from termdoctor.renderer import apply_context
    return apply_context(template, error)


def educational_content(rule: ErrorRule, error: ParsedError, mode: str = "standard") -> dict:
    """Build a user-facing payload; no guesses beyond the matching rule."""
    if mode not in {"beginner", "standard"}:
        raise ValueError("Unsupported mode")
    if mode == "beginner":
        location = f"{error.file_path}:{error.line_number}" if error.file_path and error.line_number else error.file_path
        where = tr("education.location_hint", location=location) if location else tr("education.location_unknown")
        # Only describe the fault in beginner mode. No code patches or install commands.
        question = _questions(get_locale()).get(rule.id)
        if question is None:
            question = _questions("en")[rule.id]
        return {
            "overview": _apply(_summaries(get_locale()).get(rule.id, rule.title), error),
            "where": where,
            "question": _apply(question, error),
            "mechanism": "",
            "causes": [],
            "actions": [],
        }
    # Technical detail and actions are only visible in standard mode.
    mechanism = _mechanisms(get_locale()).get(rule.id, "")
    return {
        "overview": _apply(rule.explanation, error),
        "where": "",
        "question": "",
        "mechanism": _apply(mechanism, error),
        "causes": [_apply(x, error) for x in rule.causes],
        "actions": [_apply(x, error) for x in rule.fixes],
    }
