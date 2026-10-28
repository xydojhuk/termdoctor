"""Run commands and (optionally) mirror output while capturing it for diagnosis.

In streaming mode the child inherits stdin; stdout and stderr are copied live to
our terminal and retained in bounded buffers. This supports ordinary input()
programs, unlike subprocess.run(capture_output=True).
"""
from __future__ import annotations

import codecs
import locale
import os
import shlex
import subprocess
import sys
import threading
import time
from collections.abc import Sequence

from termdoctor.models import CommandResult

CommandInput = str | Sequence[str]
MAX_CAPTURE_CHARS = 512_000


def format_command(command: CommandInput) -> str:
    if isinstance(command, str):
        return command
    return subprocess.list2cmdline(list(command)) if os.name == "nt" else shlex.join(list(command))


def _tail(buffer: str, text: str, limit: int) -> str:
    return (buffer + text)[-limit:]


def _mirror(pipe, target, captured: list[str], limit: int) -> None:
    encoding = getattr(target, "encoding", None) or locale.getpreferredencoding(False) or "utf-8"
    decoder = codecs.getincrementaldecoder(encoding)(errors="replace")
    collected = ""
    try:
        while True:
            chunk = os.read(pipe.fileno(), 4096)
            if not chunk:
                break
            text = decoder.decode(chunk)
            collected = _tail(collected, text, limit)
            if target is not None:
                try:
                    target.write(text)
                    target.flush()
                except (BrokenPipeError, OSError, ValueError):
                    pass
        final = decoder.decode(b"", final=True)
        if final:
            collected = _tail(collected, final, limit)
            if target is not None:
                try:
                    target.write(final)
                    target.flush()
                except (BrokenPipeError, OSError, ValueError):
                    pass
    finally:
        captured.append(collected)
        pipe.close()


def run_shell_command(
    command: CommandInput,
    *,
    stream: bool = False,
    timeout: float | None = None,
    capture_limit: int = MAX_CAPTURE_CHARS,
) -> CommandResult:
    """Run a command; return the exit code and retained output.

    List commands are executed without a shell. A string intentionally uses the
    system shell for backwards compatibility. No implicit shell is used for the
    new ``td file.py`` shorthand.
    """
    if timeout is not None and timeout <= 0:
        raise ValueError("timeout must be positive")
    if capture_limit < 1:
        raise ValueError("capture_limit must be positive")
    started = time.perf_counter()
    cwd = os.getcwd()
    display = format_command(command)
    argv = command if isinstance(command, str) else list(command)
    env = os.environ.copy()
    if stream and not isinstance(command, str):
        # Prevent Python buffering its prompts when stdout is a pipe.
        executable = os.path.basename(str(argv[0])).lower().removesuffix(".exe") if argv else ""
        if executable.startswith("python") or executable == "py":
            env.setdefault("PYTHONUNBUFFERED", "1")
    try:
        proc = subprocess.Popen(
            argv,
            shell=isinstance(command, str),
            cwd=cwd,
            env=env,
            stdin=None if stream else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        return CommandResult(display, cwd, 127 if isinstance(exc, FileNotFoundError) else 1,
                             "", f"{type(exc).__name__}: {exc}", time.perf_counter() - started)

    out: list[str] = []
    err: list[str] = []
    a = threading.Thread(
        target=_mirror,
        args=(proc.stdout, sys.stdout if stream else None, out, capture_limit),
        daemon=True,
    )
    b = threading.Thread(
        target=_mirror,
        args=(proc.stderr, sys.stderr if stream else None, err, capture_limit),
        daemon=True,
    )
    a.start()
    b.start()
    timed_out = False
    try:
        code = proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        code = 124
        timed_out = True
    except KeyboardInterrupt:
        try:
            proc.terminate()
        except OSError:
            pass
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        a.join()
        b.join()
        raise
    a.join()
    b.join()
    stdout = out[0] if out else ""
    stderr = err[0] if err else ""
    if timed_out:
        message = "\nTermDoctor: command timed out."
        stderr += message
        if stream:
            sys.stderr.write(message + "\n")
    return CommandResult(display, cwd, code, stdout, stderr, time.perf_counter() - started)
