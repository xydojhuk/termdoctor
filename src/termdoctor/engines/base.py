from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from termdoctor.models import (
    CommandResult,
    DiagnosticSection,
    ErrorRule,
    FrameworkDiagnosisContext,
    ModuleDiagnosisContext,
    ParsedError,
)


@dataclass
class EngineDiagnosis:
    language: str
    display_name: str
    parsed_error: ParsedError
    rule: ErrorRule | None
    command_result: CommandResult | None = None
    sections: list[DiagnosticSection] = field(default_factory=list)
    environment: object | None = None
    module_context: ModuleDiagnosisContext | None = None
    framework_context: FrameworkDiagnosisContext | None = None


class BaseEngine(ABC):
    language: str = "unknown"
    display_name: str = "Unknown"

    @abstractmethod
    def can_handle_command(self, command: str | list[str]) -> bool:
        raise NotImplementedError

    @abstractmethod
    def can_handle_text(self, text: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse_error(self, text: str) -> ParsedError | None:
        raise NotImplementedError

    @abstractmethod
    def find_rule(self, parsed_error: ParsedError, locale: str | None = None) -> ErrorRule | None:
        raise NotImplementedError

    @abstractmethod
    def diagnose(
        self,
        text: str,
        command_result: CommandResult | None = None,
        cwd: Path | None = None,
        locale: str | None = None,
        python_executable: str | None = None,
    ) -> EngineDiagnosis | None:
        raise NotImplementedError
