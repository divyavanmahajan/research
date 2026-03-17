"""Typed exceptions for infomodel-dbt-generator."""


class ParseError(Exception):
    """Raised when the YAML file cannot be parsed."""


class ModelValidationError(Exception):
    """Raised when the conceptual model fails semantic validation."""

    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors or []

    def __str__(self) -> str:
        if self.errors:
            detail = "\n  - " + "\n  - ".join(self.errors)
            return f"{super().__str__()}{detail}"
        return super().__str__()
