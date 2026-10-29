# Security Policy

TermDoctor is an early-stage, locally running developer tool. It executes user-supplied commands and analyzes their output. It is **not** a sandbox and does not provide a security boundary for untrusted code.

## Supported versions

Security-related fixes are evaluated for the active development branch. No formal security maintenance or backport guarantees are currently offered for older releases.

## Reporting a vulnerability

**Do not disclose exploit details, private data, credentials, or reproducible attacks in a public GitHub issue.**

1. If GitHub's **Report a vulnerability** option is available on the repository's [Security](https://github.com/xydojhuk/termdoctor/security) page, use it to send a private report.
2. If that option is not available, open a **non-sensitive** [GitHub issue](https://github.com/xydojhuk/termdoctor/issues/new) requesting a private reporting channel. Do not include vulnerability details in that public request.

Useful details for a private report include the affected version or commit, operating system, Python version, impact, and the minimum steps required to reproduce the issue safely.

No fixed response time, bounty, or remediation SLA is promised.

## Sensitive data and command execution

- TermDoctor runs the command you ask it to run. Do not execute untrusted scripts expecting TermDoctor to isolate them.
- Failure history is disabled by default. It can be enabled with `td set history on` and disabled with `td set history off`.
- If history is enabled, common secrets are redacted on a best-effort basis; unfamiliar secret formats may remain in output.
- Avoid including credentials or private information in bug reports, screenshots, generated Markdown reports, or diagnostic logs.
