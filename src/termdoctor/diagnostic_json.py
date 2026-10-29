"""Versioned machine-readable diagnostic output."""
from __future__ import annotations

import json
from typing import Any

from termdoctor import __version__
from termdoctor.engines.base import EngineDiagnosis
from termdoctor.renderer import apply_context
from termdoctor.education import educational_content, get_active_mode
from termdoctor.i18n import get_locale


def diagnosis_to_dict(diagnosis: EngineDiagnosis, *, include_raw: bool = False, mode: str | None = None) -> dict[str, Any]:
    error = diagnosis.parsed_error
    rule = diagnosis.rule
    selected_mode = mode or get_active_mode()
    educational = educational_content(rule, error, selected_mode) if rule is not None else None
    data: dict[str, Any] = {
        "schema_version": 1,
        "termdoctor_version": __version__,
        "language": diagnosis.language,
        "interface_locale": get_locale(),
        "explanation_mode": selected_mode,
        "error": {
            "type": error.error_type,
            "message": error.message,
            "file": error.file_path,
            "line": error.line_number,
        },
        "rule": None if rule is None else {
            "id": rule.id,
            "title": rule.title,
            "explanation": apply_context(rule.explanation, error) if selected_mode == "standard" else educational["overview"],
            "possible_causes": [apply_context(x, error) for x in rule.causes] if selected_mode == "standard" else [],
            "suggestions": [apply_context(x, error) for x in rule.fixes] if selected_mode == "standard" else [],
            "educational": educational,
        },
    }
    if include_raw:
        data["raw_traceback"] = error.raw_text
    return data


def diagnosis_to_json(diagnosis: EngineDiagnosis, *, include_raw: bool = False, mode: str | None = None) -> str:
    return json.dumps(diagnosis_to_dict(diagnosis, include_raw=include_raw, mode=mode), ensure_ascii=False, indent=2)
