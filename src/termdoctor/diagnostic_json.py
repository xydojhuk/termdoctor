"""Stable, versioned machine-readable diagnosis for future editor integrations."""
from __future__ import annotations

import json
from typing import Any

from termdoctor import __version__
from termdoctor.engines.base import EngineDiagnosis
from termdoctor.renderer import apply_context


def diagnosis_to_dict(diagnosis: EngineDiagnosis, *, include_raw: bool = False) -> dict[str, Any]:
    error = diagnosis.parsed_error
    rule = diagnosis.rule
    data: dict[str, Any] = {
        "schema_version": 1,
        "termdoctor_version": __version__,
        "language": diagnosis.language,
        "error": {
            "type": error.error_type,
            "message": error.message,
            "file": error.file_path,
            "line": error.line_number,
        },
        "rule": None if rule is None else {
            "id": rule.id,
            "title": rule.title,
            "explanation": apply_context(rule.explanation, error),
            "possible_causes": [apply_context(x, error) for x in rule.causes],
            "suggestions": [apply_context(x, error) for x in rule.fixes],
        },
    }
    if include_raw:
        data["raw_traceback"] = error.raw_text
    return data


def diagnosis_to_json(diagnosis: EngineDiagnosis, *, include_raw: bool = False) -> str:
    return json.dumps(diagnosis_to_dict(diagnosis, include_raw=include_raw), ensure_ascii=False, indent=2)
