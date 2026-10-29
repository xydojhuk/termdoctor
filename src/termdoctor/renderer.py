from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from termdoctor import __version__
from termdoctor.core.history import format_history_time, trim_text
from termdoctor.i18n import tr
from termdoctor.education import educational_content
from termdoctor.models import (
    CommandResult,
    DiagnosticSection,
    ErrorRule,
    ParsedError,
    PythonDoctorResult,
    PythonEnvironment,
)


console = Console()


def render_success(command_result: CommandResult) -> None:
    console.print(
        Panel(
            f"[bold green]{tr('run.success')}[/bold green]\n"
            f"{tr('run.duration', seconds=command_result.duration_seconds)}",
            title=tr("run.success_title"),
            border_style="green",
        )
    )
    if command_result.stdout.strip():
        console.print()
        console.print(Panel(command_result.stdout.rstrip(), title="stdout", border_style="green"))
    if command_result.stderr.strip():
        console.print()
        console.print(Panel(command_result.stderr.rstrip(), title="stderr", border_style="yellow"))


def render_command_output(command_result: CommandResult) -> None:
    if command_result.stdout.strip():
        console.print()
        console.print(Panel(command_result.stdout.rstrip(), title="stdout", border_style="blue"))
    if command_result.stderr.strip():
        console.print()
        console.print(Panel(command_result.stderr.rstrip(), title="stderr", border_style="red"))


def render_diagnosis(
    parsed_error: ParsedError,
    rule: ErrorRule | None,
    command_result: CommandResult | None = None,
    sections: list[DiagnosticSection] | None = None,
    language_name: str = "Python",
    mode: str = "standard",
) -> None:
    console.print()
    console.print(
        Panel(
            build_error_summary(parsed_error, command_result) if mode == "standard"
            else build_learner_summary(parsed_error),
            title=f"[bold red]TermDoctor v{__version__} · {parsed_error.error_type}[/bold red]",
            border_style="red",
        )
    )
    if rule is None:
        render_unknown_rule(parsed_error)
        return

    content = educational_content(rule, parsed_error, mode=mode)
    if mode == "beginner":
        for key, value in (
            ("education.beginner_what", content["overview"]),
            ("education.beginner_where", content["where"]),
            ("education.beginner_hint", content["question"]),
        ):
            console.print()
            console.print(Panel(value, title=tr(key), border_style="cyan"))
        return

    if parsed_error.source_context:
        console.print()
        console.print(Panel("\n".join(parsed_error.source_context), title=tr("diagnosis.source_context"), border_style="blue"))

    for section in sections or []:
        render_diagnostic_section(section)

    console.print()
    console.print(Panel(content["overview"], title=tr("education.standard_what"), border_style="yellow"))
    if content["mechanism"]:
        console.print()
        console.print(Panel(content["mechanism"], title=tr("education.standard_mechanism"), border_style="blue"))

    if content["causes"]:
        table = Table(title=tr("diagnosis.likely_causes"), show_header=False)
        table.add_column("#", width=3, style="cyan")
        table.add_column(tr("diagnosis.cause"))
        for index, cause in enumerate(content["causes"], 1):
            table.add_row(str(index), cause)
        console.print()
        console.print(table)

    if content["actions"]:
        table = Table(title=tr("diagnosis.what_to_try"), show_header=False)
        table.add_column("#", width=3, style="cyan")
        table.add_column(tr("diagnosis.suggestion"))
        for index, action in enumerate(content["actions"], 1):
            table.add_row(str(index), action)
        console.print()
        console.print(table)


def build_learner_summary(parsed_error: ParsedError) -> str:
    message = parsed_error.message
    summary = f"{tr('diagnosis.message')}: {message}" if message else parsed_error.error_type
    if parsed_error.file_path:
        path = parsed_error.file_path
        if parsed_error.line_number is not None:
            path += f":{parsed_error.line_number}"
        summary += f"\n{tr('diagnosis.location')}: {path}"
    return summary


def render_diagnostic_section(section: DiagnosticSection) -> None:
    if section.fields:
        table = Table(title=tr(section.title_key), show_header=True, header_style="bold magenta")
        table.add_column(tr("environment.item"), style="cyan")
        table.add_column(tr("environment.value"))
        for field in section.fields:
            table.add_row(tr(field.label_key), field.value)
        console.print()
        console.print(table)

    if section.suggestions:
        table = Table(title=tr("section.suggestions"), show_header=True, header_style="bold green")
        table.add_column(tr("diagnosis.item"), style="cyan", width=4, justify="right")
        table.add_column(tr("diagnosis.suggestion"))
        for index, suggestion in enumerate(section.suggestions, 1):
            table.add_row(str(index), tr(suggestion.key, **suggestion.params))
        console.print()
        console.print(table)


def render_python_environment(environment: PythonEnvironment) -> None:
    console.print()
    console.print(
        Panel(
            tr("environment.intro"),
            title=f"[bold blue]{tr('environment.intro_title')}[/bold blue]",
            border_style="blue",
        )
    )
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column(tr("environment.item"), style="cyan")
    table.add_column(tr("environment.value"))
    table.add_row(tr("environment.python_version"), environment.python_version)
    table.add_row(tr("environment.python_executable"), environment.python_executable)
    table.add_row(tr("environment.current_directory"), environment.current_dir)
    table.add_row(tr("environment.project_root"), environment.project_root)
    table.add_row(tr("environment.virtual_environment"), tr("common.active") if environment.venv_active else tr("common.not_active"))
    table.add_row(tr("environment.active_venv_path"), environment.active_venv_path or "-")
    table.add_row(tr("environment.project_venv"), environment.project_venv_path or "-")
    table.add_row(tr("environment.activation_command"), environment.activation_command or "-")
    table.add_row(tr("environment.requirements"), ", ".join(environment.dependency_info.dependency_files) or "-")
    table.add_row(tr("environment.pyproject"), environment.pyproject_file or "-")
    table.add_row(tr("environment.env"), environment.env_file or "-")
    table.add_row(tr("environment.env_example"), environment.env_example_file or "-")
    table.add_row(tr("environment.tests"), environment.tests_dir or "-")
    console.print(table)
    render_dependency_summary(environment)
    render_detected_frameworks(environment)


def render_dependency_summary(environment: PythonEnvironment) -> None:
    sources = environment.dependency_info.source_dependencies
    if not any(sources.values()):
        console.print()
        console.print(Panel(tr("environment.dependencies_empty"), title=tr("environment.dependencies_title"), border_style="yellow"))
        return
    table = Table(title=tr("environment.dependencies_title"), show_header=True, header_style="bold green")
    table.add_column(tr("environment.source"), style="cyan")
    table.add_column(tr("environment.packages"))
    for source, packages in sources.items():
        if packages:
            table.add_row(source, ", ".join(packages))
    console.print()
    console.print(table)


def render_detected_frameworks(environment: PythonEnvironment) -> None:
    detected = environment.framework_info.detected_frameworks
    if not detected:
        console.print()
        console.print(Panel(tr("environment.frameworks_empty"), title=tr("environment.frameworks_title"), border_style="yellow"))
        return
    table = Table(title=tr("environment.frameworks_title"), show_header=True, header_style="bold green")
    table.add_column(tr("environment.framework"), style="cyan")
    table.add_column(tr("environment.evidence"))
    for framework in detected:
        table.add_row(framework.name, ", ".join(framework.evidence) or "-")
    console.print()
    console.print(table)


def render_python_doctor(result: PythonDoctorResult) -> None:
    console.print()
    console.print(Panel(tr("doctor.intro"), title=f"[bold blue]{tr('doctor.title')}[/bold blue]", border_style="blue"))
    table = Table(title=tr("doctor.checks"), show_header=True, header_style="bold cyan")
    table.add_column(tr("doctor.status"), width=12)
    table.add_column(tr("doctor.check"))
    status_labels = {
        "ok": "[green]" + tr("common.ok") + "[/green]",
        "warn": "[yellow]" + tr("common.warn") + "[/yellow]",
        "info": "[blue]" + tr("common.info") + "[/blue]",
    }
    for check in result.checks:
        table.add_row(status_labels[check.status], tr(check.label_key, **check.params))
    console.print(table)

    if result.warnings:
        warnings = Table(title=tr("doctor.warnings"), show_header=True, header_style="bold yellow")
        warnings.add_column(tr("diagnosis.item"), style="cyan", width=4, justify="right")
        warnings.add_column(tr("doctor.warning"))
        for index, warning in enumerate(result.warnings, 1):
            warnings.add_row(str(index), tr(warning.key, **warning.params))
        console.print()
        console.print(warnings)

    if result.suggestions:
        suggestions = Table(title=tr("doctor.suggestions"), show_header=True, header_style="bold green")
        suggestions.add_column(tr("diagnosis.item"), style="cyan", width=4, justify="right")
        suggestions.add_column(tr("diagnosis.suggestion"))
        for index, suggestion in enumerate(result.suggestions, 1):
            suggestions.add_row(str(index), tr(suggestion.key, **suggestion.params))
        console.print()
        console.print(suggestions)

    console.print()
    render_python_environment(result.environment)


def render_unknown_rule(parsed_error: ParsedError) -> None:
    console.print()
    console.print(Panel(tr("diagnosis.unknown_rule"), title=tr("diagnosis.unknown_rule_title"), border_style="yellow"))


def render_no_python_error_found(text: str) -> None:
    console.print()
    console.print(Panel(tr("diagnosis.no_error"), title=tr("diagnosis.no_error_title"), border_style="yellow"))
    if text.strip():
        preview = text.strip()
        if len(preview) > 1500:
            preview = preview[:1500] + "\n..."
        console.print()
        console.print(Panel(preview, title=tr("diagnosis.input_preview"), border_style="blue"))


def render_history(items: list[dict]) -> None:
    if not items:
        console.print(Panel(tr("history.empty"), title=tr("history.title"), border_style="yellow"))
        return
    table = Table(title=tr("history.title"), show_lines=False)
    table.add_column(tr("diagnosis.item"), style="cyan", width=4, justify="right")
    table.add_column(tr("history.time"), style="dim")
    table.add_column(tr("history.error"), style="red")
    table.add_column(tr("history.exit"), justify="right")
    table.add_column(tr("history.message"))
    table.add_column(tr("history.command"))
    for index, item in enumerate(items, 1):
        table.add_row(
            str(index),
            format_history_time(item.get("timestamp")),
            item.get("error_type") or tr("common.unknown"),
            str(item.get("exit_code") if item.get("exit_code") is not None else ""),
            trim_text(item.get("error_message") or "", 45),
            trim_text(item.get("command") or "", 50),
        )
    console.print(table)


def build_error_summary(parsed_error: ParsedError, command_result: CommandResult | None = None) -> str:
    lines: list[str] = []
    if command_result:
        lines.extend(
            [
                f"{tr('diagnosis.command')}: {command_result.command}",
                f"{tr('diagnosis.exit_code')}: {command_result.exit_code}",
                f"{tr('diagnosis.working_directory')}: {command_result.cwd}",
            ]
        )
    lines.append(f"{tr('diagnosis.error')}: {parsed_error.error_type}")
    if parsed_error.full_error_type and parsed_error.full_error_type != parsed_error.error_type:
        lines.append(f"{tr('diagnosis.full_error_type')}: {parsed_error.full_error_type}")
    if parsed_error.message:
        lines.append(f"{tr('diagnosis.message')}: {parsed_error.message}")
    if parsed_error.file_path:
        location = parsed_error.file_path
        if parsed_error.line_number is not None:
            location += f":{parsed_error.line_number}"
        lines.append(f"{tr('diagnosis.location')}: {location}")
    if len(parsed_error.exception_chain) > 1:
        lines.append(f"{tr('diagnosis.exception_chain')}: {' -> '.join(parsed_error.exception_chain)}")
    return "\n".join(lines)


def apply_context(text: str, parsed_error: ParsedError) -> str:
    context = {
        "error_type": parsed_error.error_type,
        "message": parsed_error.message,
        "file_path": parsed_error.file_path or tr("common.unknown"),
        "line_number": str(parsed_error.line_number) if parsed_error.line_number else tr("common.unknown"),
        "module": parsed_error.extracted.get("module", "module"),
        "name": parsed_error.extracted.get("name", "name"),
        "key": parsed_error.extracted.get("key", "key"),
        "path": parsed_error.extracted.get("path", "path"),
        "attribute": parsed_error.extracted.get("attribute", "attribute"),
        "relation": parsed_error.extracted.get("relation", "relation"),
        "field": parsed_error.extracted.get("field", "field"),
    }
    try:
        return text.format(**context)
    except (KeyError, ValueError):
        return text
