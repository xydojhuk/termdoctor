from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

from termdoctor import __version__
from termdoctor.core.history import (
    clear_history,
    get_history_text,
    get_last_history_item,
    load_history,
    save_failed_run,
)
from termdoctor.core.runner import run_shell_command
from termdoctor.core.shortcuts import expand_script_shortcut
from termdoctor.diagnostic_json import diagnosis_to_json
from termdoctor.engines.registry import get_default_registry, get_engine_by_language, get_language_detector
from termdoctor.engines.python.environment import diagnose_python_project, get_python_environment
from termdoctor.i18n import (
    SUPPORTED_LOCALES,
    get_locale,
    history_enabled,
    save_history_enabled,
    resolve_locale,
    set_locale,
    set_saved_locale,
    tr,
)
from termdoctor.renderer import (
    console,
    render_command_output,
    render_diagnosis,
    render_history,
    render_no_python_error_found,
    render_python_doctor,
    render_python_environment,
    render_success,
)
from termdoctor.report import build_markdown_report, write_report


app = typer.Typer(
    name="termdoctor",
    help="Explain Python terminal errors and suggest practical fixes.",
    add_completion=False,
    no_args_is_help=True,
)
doctor_app = typer.Typer(name="doctor", help="Run project-level diagnostics.", add_completion=False, no_args_is_help=True)
config_app = typer.Typer(name="config", help="View or change TermDoctor settings.", add_completion=False, no_args_is_help=False)
set_app = typer.Typer(name="set", help="Save user preferences.", add_completion=False)
app.add_typer(doctor_app, name="doctor")
app.add_typer(config_app, name="config")
app.add_typer(set_app, name="set")
app.add_typer(set_app, name="change", hidden=True)


def version_callback(value: bool) -> None:
    if value:
        console.print(f"TermDoctor {__version__}")
        raise typer.Exit()


@app.callback()
def callback(
    lang: str | None = typer.Option(
        None,
        "--lang",
        help="Interface language: en or ru. Aliases such as eng and rus are accepted.",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        help="Show TermDoctor version.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    try:
        set_locale(lang)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2)


@app.command(
    "run",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def run_command(
    ctx: typer.Context,
    command: str | None = typer.Argument(
        None,
        help='Command to run, for example "python main.py".',
    ),
    output_format: str = typer.Option("text", "--format", help="text or json (JSON capture is non-interactive)."),
    timeout: float | None = typer.Option(None, "--timeout", help="Stop a long-running process after N seconds."),
    no_history: bool = typer.Option(
        False,
        "--no-history",
        help="Do not save this failed command or its output to TermDoctor history.",
    ),
) -> None:
    command_to_run = build_command_input(command, list(ctx.args))
    if command_to_run is None:
        console.print(f"[red]{tr('common.error')}:[/red] {tr('run.missing_command')}")
        console.print(tr("run.example_1"))
        console.print(tr("run.example_2"))
        raise typer.Exit(code=1)

    if output_format not in {"text", "json"}:
        console.print("[red]--format must be text or json[/red]")
        raise typer.Exit(code=2)
    try:
        # Human-friendly execution mirrors stdout/stderr live; JSON capture stays
        # silent so downstream tools receive exactly one machine-readable object.
        command_result = run_shell_command(
            command_to_run, stream=output_format == "text", timeout=timeout,
        )
    except KeyboardInterrupt:
        raise typer.Exit(code=130)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2)
    if command_result.exit_code == 0:
        if output_format == "json":
            sys.stdout.write(json.dumps({"schema_version": 1, "success": True, "exit_code": 0}) + "\n")
        raise typer.Exit(code=0)

    text_to_parse = command_result.diagnostic_text
    engine = get_language_detector().detect_for_command(command_to_run, text_to_parse)
    if engine is None:
        if output_format == "json":
            sys.stdout.write(json.dumps({"schema_version": 1, "success": False, "exit_code": command_result.exit_code, "diagnosis": None}) + "\n")
        else:
            render_no_python_error_found("")
        raise typer.Exit(code=command_result.exit_code)

    python_executable = None
    if isinstance(command_to_run, list) and engine.language == "python":
        from termdoctor.engines.python.engine import is_python_executable, normalize_executable
        if command_to_run and is_python_executable(normalize_executable(command_to_run[0])):
            python_executable = command_to_run[0]
    diagnosis = engine.diagnose(
        text_to_parse,
        command_result=command_result,
        cwd=Path(command_result.cwd),
        locale=get_locale(),
        python_executable=python_executable,
    )
    if diagnosis is None:
        if output_format == "json":
            sys.stdout.write(json.dumps({"schema_version": 1, "success": False, "exit_code": command_result.exit_code, "diagnosis": None}) + "\n")
        else:
            render_no_python_error_found("")
        raise typer.Exit(code=command_result.exit_code)

    if not no_history and history_enabled():
        save_failed_run(command_result, diagnosis.parsed_error)
    if output_format == "json":
        sys.stdout.write(json.dumps({"schema_version": 1, "success": False, "exit_code": command_result.exit_code,
                                  "diagnosis": json.loads(diagnosis_to_json(diagnosis))}, ensure_ascii=False) + "\n")
    else:
        render_engine_diagnosis(diagnosis)
    raise typer.Exit(code=command_result.exit_code)


def build_command_input(command: str | None, extra_args: list[str]) -> str | list[str] | None:
    if command and extra_args:
        return [command, *extra_args]
    if command:
        stripped = command.strip()
        return stripped if stripped else None
    return extra_args or None


def render_engine_diagnosis(diagnosis) -> None:
    render_diagnosis(
        diagnosis.parsed_error,
        diagnosis.rule,
        diagnosis.command_result,
        sections=diagnosis.sections,
        language_name=diagnosis.display_name,
    )


@app.command("languages")
def show_languages() -> None:
    console.print(f"[bold]{tr('languages.title')}[/bold]")
    for code, name in SUPPORTED_LOCALES.items():
        console.print(f"- {name} ({code})")
    console.print()
    console.print(f"[bold]{tr('languages.engines_title')}[/bold]")
    for engine in get_default_registry():
        console.print(f"- {engine.display_name} ({engine.language})")


@app.command("env")
def show_environment() -> None:
    render_python_environment(get_python_environment())


@doctor_app.command("python")
def doctor_python() -> None:
    render_python_doctor(diagnose_python_project())


@app.command("explain")
def explain_error(
    source: str = typer.Argument("last", help='Use "last" or provide a traceback file/path.'),
    engine: str | None = typer.Option(None, "--engine", "--lang", help="Force a programming-language engine, for example python."),
    output_format: str = typer.Option("text", "--format", help="text or json"),
) -> None:
    if output_format not in {"text", "json"}:
        console.print("[red]--format must be text or json[/red]")
        raise typer.Exit(code=2)
    text, cwd = load_explain_source(source)
    selected = get_engine_for_explain(text, engine_name=engine)
    if selected is None:
        if engine:
            console.print(f"[red]{tr('errors.unsupported_engine', engine=engine)}[/red]")
        else:
            render_no_python_error_found(text)
        raise typer.Exit(code=1)
    diagnosis = selected.diagnose(text, cwd=cwd, locale=get_locale())
    if diagnosis is None:
        render_no_python_error_found(text)
        raise typer.Exit(code=1)
    if output_format == "json":
        sys.stdout.write(diagnosis_to_json(diagnosis) + "\n")
    else:
        render_engine_diagnosis(diagnosis)


@app.command("report")
def create_report(
    source: str = typer.Argument("last", help='Use "last" or provide a traceback file/path.'),
    output: str | None = typer.Option(None, "--output", "-o", help="Write the Markdown report to a file."),
    show_raw: bool = typer.Option(True, "--show-raw/--no-raw", help="Include or exclude the raw traceback."),
    engine: str | None = typer.Option(None, "--engine", "--lang", help="Force a programming-language engine, for example python."),
) -> None:
    try:
        markdown = build_markdown_report(source, include_raw=show_raw, engine_name=engine)
    except ValueError as exc:
        console.print(f"[red]{tr('common.error')}:[/red] {exc}")
        raise typer.Exit(code=1)
    if output:
        path = write_report(markdown, output)
        console.print(f"[green]{tr('report.written', path=path)}[/green]")
        raise typer.Exit(code=0)
    console.print(markdown)


@app.command("paste")
def paste_error(
    engine: str | None = typer.Option(None, "--engine", "--lang", help="Force a programming-language engine, for example python."),
) -> None:
    console.print(f"[bold]{tr('paste.title')}[/bold]")
    console.print(tr("paste.finish"))
    console.print()
    text = sys.stdin.read()
    selected = get_engine_for_explain(text, engine_name=engine)
    if selected is None:
        render_no_python_error_found(text)
        raise typer.Exit(code=1)
    diagnosis = selected.diagnose(text, locale=get_locale())
    if diagnosis is None:
        render_no_python_error_found(text)
        raise typer.Exit(code=1)
    render_engine_diagnosis(diagnosis)


@app.command("history")
def show_history(
    limit: int = typer.Option(10, "--limit", "-l", help="Number of history items to show."),
) -> None:
    items = load_history()
    if limit > 0:
        items = items[-limit:]
    render_history(items)


@app.command("clear")
def clear_saved_history() -> None:
    clear_history()
    console.print(f"[green]{tr('history.cleared')}[/green]")


@config_app.command("language")
def config_language(
    value: str | None = typer.Argument(None, help="Language to save as default: en or ru."),
) -> None:
    if value is None:
        locale = resolve_locale()
        console.print(tr("config.current", language=f"{SUPPORTED_LOCALES[locale]} ({locale})"))
        return
    try:
        locale = set_saved_locale(value)
        set_locale(locale)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2)
    console.print(tr("config.saved", language=f"{SUPPORTED_LOCALES[locale]} ({locale})"))


@config_app.callback(invoke_without_command=True)
def show_config(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is not None:
        return
    console.print(f"Language: {resolve_locale()}")
    console.print(f"History: {'on' if history_enabled() else 'off'}")
    console.print("Explanation mode: standard (educational modes planned for v0.4.1)")


@set_app.command("lang")
def set_language(value: str) -> None:
    config_language(value)


@set_app.command("history")
def set_history(value: str) -> None:
    if value.lower() not in {"on", "off"}:
        console.print("[red]Use on or off.[/red]")
        raise typer.Exit(code=2)
    save_history_enabled(value.lower() == "on")
    console.print(f"History: {value.lower()}")


def load_explain_source(source: str) -> tuple[str, Path | None]:
    if source == "last":
        last_item = get_last_history_item()
        if not last_item:
            console.print(f"[yellow]{tr('history.no_history')}[/yellow]")
            console.print(tr("history.run_first"))
            raise typer.Exit(code=1)
        cwd_value = last_item.get("cwd")
        return get_history_text(last_item), Path(cwd_value) if cwd_value else None

    path = Path(source)
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8"), path.resolve().parent
    return source, None


def load_explain_text(source: str) -> str:
    return load_explain_source(source)[0]


def get_engine_for_explain(
    text: str,
    engine_name: str | None = None,
    lang: str | None = None,
):
    requested = engine_name or lang
    return get_engine_by_language(requested) if requested else get_language_detector().detect_for_text(text)


def main() -> None:
    try:
        args = expand_script_shortcut(sys.argv[1:])
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(2)
    app(args=args, prog_name=Path(sys.argv[0]).name)
