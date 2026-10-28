from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from termdoctor.core.platform_utils import get_activation_command
from termdoctor.core.project import find_project_root
from termdoctor.engines.python.dependencies import collect_dependency_info, dependency_exists
from termdoctor.engines.python.frameworks import detect_frameworks
from termdoctor.engines.python.package_hints import get_install_name, get_package_hint
from termdoctor.models import (
    DiagnosticMessage,
    DoctorCheck,
    ModuleDiagnosisContext,
    PythonDoctorResult,
    PythonEnvironment,
)


def probe_python(executable: str | None) -> dict[str, str] | None:
    """Read the *target* Python environment rather than pipx's interpreter."""
    if not executable:
        return None
    script = (
        "import json,os,sys; print(json.dumps({"
        "'executable':sys.executable,'version':'.'.join(map(str,sys.version_info[:3])),"
        "'prefix':sys.prefix,'base_prefix':sys.base_prefix,"
        "'venv':sys.prefix if sys.prefix!=sys.base_prefix else ''}))"
    )
    try:
        result = subprocess.run([executable, "-c", script], capture_output=True,
                                text=True, timeout=4, check=True)
        data = json.loads(result.stdout)
        return data if isinstance(data, dict) else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def get_python_environment(cwd: Path | None = None, python_executable: str | None = None) -> PythonEnvironment:
    current_dir = (cwd or Path.cwd()).resolve()
    project_root = find_project_root(current_dir)
    dependency_info = collect_dependency_info(project_root)
    framework_info = detect_frameworks(project_root, dependency_info.all_dependencies)

    probe = probe_python(python_executable)
    target_executable = str(probe.get("executable")) if probe else (python_executable or sys.executable)
    if probe:
        active_venv_path = str(probe.get("venv") or "") or (
            str(probe["prefix"]) if probe.get("prefix") != probe.get("base_prefix") else None
        )
        venv_active = bool(active_venv_path)
        version = str(probe.get("version") or "unknown")
    else:
        active_venv_path = get_active_venv_path() if python_executable is None else None
        venv_active = is_venv_active() if python_executable is None else False
        version = get_python_version() if python_executable is None else "unknown"
    project_venv_path = find_project_venv(project_root)
    activation_command = get_activation_command(project_venv_path)

    return PythonEnvironment(
        python_version=version,
        python_executable=target_executable,
        current_dir=str(current_dir),
        project_root=str(project_root),
        cwd=str(current_dir),
        venv_active=venv_active,
        active_venv_path=active_venv_path,
        project_venv_path=project_venv_path,
        activation_command=activation_command,
        requirements_file=dependency_info.requirements_file,
        pyproject_file=dependency_info.pyproject_file,
        env_file=_existing_path(project_root / ".env"),
        env_example_file=_existing_path(project_root / ".env.example"),
        tests_dir=_existing_path(project_root / "tests"),
        dependency_info=dependency_info,
        framework_info=framework_info,
    )


def _existing_path(path: Path) -> str | None:
    return str(path) if path.exists() else None


def get_python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def is_venv_active() -> bool:
    return bool(os.environ.get("VIRTUAL_ENV")) or sys.prefix != sys.base_prefix


def get_active_venv_path() -> str | None:
    return os.environ.get("VIRTUAL_ENV") or (sys.prefix if sys.prefix != sys.base_prefix else None)


def find_project_venv(cwd: Path | None = None) -> str | None:
    root = (cwd or Path.cwd()).resolve()
    for name in (".venv", "venv", "env"):
        candidate = root / name
        if candidate.exists() and candidate.is_dir():
            return str(candidate)
    return None


def get_top_level_module(module_name: str) -> str:
    return module_name.strip().split(".", 1)[0]


def is_standard_library_module(module_name: str) -> bool:
    top_level = get_top_level_module(module_name)
    stdlib_names = getattr(sys, "stdlib_module_names", set())
    return top_level in stdlib_names or top_level in sys.builtin_module_names


def find_local_module(module_name: str, project_root: Path, current_dir: Path) -> str | None:
    top_level = get_top_level_module(module_name)
    relative_parts = module_name.split(".")
    candidates: list[Path] = []
    for base in (current_dir, project_root, project_root / "src"):
        candidates.extend(
            [
                base.joinpath(*relative_parts).with_suffix(".py"),
                base.joinpath(*relative_parts, "__init__.py"),
                base / f"{top_level}.py",
                base / top_level / "__init__.py",
            ]
        )
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.exists() and resolved.is_file():
            return str(resolved)
    return None


def build_module_diagnosis_context(module_name: str, cwd: Path | None = None, python_executable: str | None = None) -> ModuleDiagnosisContext:
    current_dir = (cwd or Path.cwd()).resolve()
    environment = get_python_environment(current_dir, python_executable)
    top_level = get_top_level_module(module_name)
    package_hint = get_package_hint(top_level)
    package_name = get_install_name(top_level)
    dependency_info = environment.dependency_info

    in_requirements = dependency_exists(package_name, dependency_info.requirements_dependencies)
    in_pyproject = dependency_exists(package_name, dependency_info.pyproject_dependencies)
    if package_hint is None:
        in_requirements = in_requirements or dependency_exists(top_level, dependency_info.requirements_dependencies)
        in_pyproject = in_pyproject or dependency_exists(top_level, dependency_info.pyproject_dependencies)

    project_root = Path(environment.project_root)
    return ModuleDiagnosisContext(
        module_name=module_name,
        top_level_module=top_level,
        package_name=package_name,
        package_hint=package_hint,
        in_requirements=in_requirements,
        in_pyproject=in_pyproject,
        has_requirements_file=bool(dependency_info.requirements_dependencies or dependency_info.requirements_file),
        has_pyproject_file=bool(environment.pyproject_file or (project_root / "Pipfile").exists()),
        venv_active=environment.venv_active,
        active_venv_path=environment.active_venv_path,
        project_venv_path=environment.project_venv_path,
        activation_command=environment.activation_command,
        python_executable=environment.python_executable,
        current_dir=environment.current_dir,
        project_root=environment.project_root,
        is_standard_library=is_standard_library_module(top_level),
        local_module_path=find_local_module(module_name, project_root, current_dir),
    )


def diagnose_python_project(cwd: Path | None = None) -> PythonDoctorResult:
    environment = get_python_environment(cwd)
    dependency_found = bool(environment.dependency_info.dependency_files)
    frameworks = environment.framework_info.detected_frameworks

    checks = [
        DoctorCheck("doctor.python_available", "ok" if environment.python_executable else "warn"),
        DoctorCheck("doctor.venv_active", "ok" if environment.venv_active else "warn"),
        DoctorCheck("doctor.project_venv_exists", "ok" if environment.project_venv_path else "info"),
        DoctorCheck("doctor.dependency_file_found", "ok" if dependency_found else "warn"),
        DoctorCheck("doctor.tests_found", "ok" if environment.tests_dir else "info"),
    ]
    if frameworks:
        checks.append(
            DoctorCheck(
                "doctor.frameworks_detected",
                "info",
                {"frameworks": ", ".join(item.name for item in frameworks)},
            )
        )
    else:
        checks.append(DoctorCheck("doctor.no_frameworks", "info"))

    warnings: list[DiagnosticMessage] = []
    suggestions: list[DiagnosticMessage] = []

    if not environment.venv_active:
        warnings.append(DiagnosticMessage("doctor.warning_venv"))
        if environment.project_venv_path:
            key = "doctor.activate_venv" if environment.activation_command else "doctor.activate_venv_generic"
            params = {"command": environment.activation_command} if environment.activation_command else {}
            suggestions.append(DiagnosticMessage(key, params))
        else:
            suggestions.append(DiagnosticMessage("doctor.create_venv"))

    if not dependency_found:
        warnings.append(DiagnosticMessage("doctor.warning_dependencies"))
        suggestions.append(DiagnosticMessage("doctor.add_dependencies"))
    else:
        if environment.dependency_info.requirements_dependencies:
            suggestions.append(DiagnosticMessage("doctor.install_requirements"))
        if environment.pyproject_file:
            suggestions.append(
                DiagnosticMessage("doctor.install_pyproject", {"python": environment.python_executable})
            )

    if environment.env_file and not environment.env_example_file:
        warnings.append(DiagnosticMessage("doctor.warning_env_example"))
        suggestions.append(DiagnosticMessage("doctor.add_env_example"))

    if not environment.tests_dir:
        warnings.append(DiagnosticMessage("doctor.warning_tests"))
        suggestions.append(DiagnosticMessage("doctor.add_tests"))

    add_framework_suggestions(environment, warnings, suggestions)
    return PythonDoctorResult(
        environment=environment,
        checks=checks,
        warnings=deduplicate_messages(warnings),
        suggestions=deduplicate_messages(suggestions),
    )


def add_framework_suggestions(
    environment: PythonEnvironment,
    warnings: list[DiagnosticMessage],
    suggestions: list[DiagnosticMessage],
) -> None:
    frameworks = environment.framework_info
    if frameworks.is_detected("Django"):
        if not (Path(environment.project_root) / "manage.py").exists():
            warnings.append(DiagnosticMessage("doctor.django_manage_missing"))
        suggestions.append(DiagnosticMessage("doctor.django"))
    for name, key in (
        ("FastAPI", "doctor.fastapi"),
        ("Flask", "doctor.flask"),
        ("Pydantic", "doctor.pydantic"),
        ("SQLAlchemy", "doctor.sqlalchemy"),
        ("Alembic", "doctor.alembic"),
        ("pytest", "doctor.pytest"),
        ("aiogram", "doctor.aiogram"),
        ("pyTelegramBotAPI", "doctor.telebot"),
    ):
        if frameworks.is_detected(name):
            suggestions.append(DiagnosticMessage(key))


def deduplicate_messages(items: list[DiagnosticMessage]) -> list[DiagnosticMessage]:
    result: list[DiagnosticMessage] = []
    seen: set[tuple[str, tuple[tuple[str, object], ...]]] = set()
    for item in items:
        marker = (item.key, tuple(sorted(item.params.items())))
        if marker not in seen:
            seen.add(marker)
            result.append(item)
    return result
