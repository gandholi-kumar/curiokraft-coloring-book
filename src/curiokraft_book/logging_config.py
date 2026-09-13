"""Logging configuration with API-key redaction.

Any log line written through this module's formatter has credential-shaped
substrings replaced with ``***REDACTED***`` before it reaches a handler. This
keeps debug logs (which are written to disk and may be shared when reporting
bugs) free of secrets.

Usage:
    from curiokraft_book.logging_config import setup_logging, RedactingFormatter

    setup_logging(level="DEBUG", log_files=["logs/pipeline.log"])
    logging.getLogger("curiokraft").info("...")
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable

# Marker substituted for any matched secret. Kept in one place so tests and
# downstream log tooling can reference it rather than hardcoding the string.
REDACTION_MARKER = "***REDACTED***"


def _compile(pattern: str, replacement: str) -> tuple[re.Pattern[str], str]:
    return re.compile(pattern), replacement


# Ordered longest-prefix-first so provider-specific patterns win over the
# generic ``api_key=...`` rule (e.g. ``sk-ant-...`` before ``sk-...``).
DEFAULT_REDACTION_RULES: list[tuple[re.Pattern[str], str]] = [
    # Anthropic keys: sk-ant-api03-...  (must precede the generic sk- rule)
    _compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}", f"sk-ant-{REDACTION_MARKER}"),
    # OpenAI keys: sk-... and sk-proj-...
    _compile(r"\bsk-(?!ant-)[A-Za-z0-9_\-]{20,}", f"sk-{REDACTION_MARKER}"),
    # Google / Gemini keys: AIza...
    _compile(r"\bAIza[A-Za-z0-9_\-]{30,}", f"AIza{REDACTION_MARKER}"),
    # AWS access key IDs
    _compile(r"\bAKIA[0-9A-Z]{16}\b", f"AKIA{REDACTION_MARKER}"),
    # Hugging Face tokens
    _compile(r"\bhf_[A-Za-z0-9]{30,}", f"hf_{REDACTION_MARKER}"),
    # Bearer tokens in Authorization headers
    _compile(r"(?i)\b(bearer\s+)[A-Za-z0-9_\-\.=]{20,}", rf"\1{REDACTION_MARKER}"),
    # x-goog-api-key: <value>  /  x-api-key: <value>
    _compile(
        r"(?i)(x-(?:goog-)?api-key[\"']?\s*[:=]\s*[\"']?)([^\s\"',}]+)",
        rf"\1{REDACTION_MARKER}",
    ),
    # api_key=..., "api_key": "...", api-key: ...
    _compile(
        r"(?i)(api[_-]?key[\"']?\s*[:=]\s*[\"']?)([^\s\"',}]{8,})([\"']?)",
        rf"\1{REDACTION_MARKER}\3",
    ),
    # password / secret / token assignments
    _compile(
        r"(?i)((?:password|passwd|secret|token)[\"']?\s*[:=]\s*[\"']?)([^\s\"',}]{6,})([\"']?)",
        rf"\1{REDACTION_MARKER}\3",
    ),
    # URL-embedded credentials: scheme://user:pass@host
    _compile(r"(https?://[^:/\s]+:)([^@/\s]+)(@)", rf"\1{REDACTION_MARKER}\3"),
]


class RedactingFormatter(logging.Formatter):
    """Formatter that redacts credential-shaped substrings from log output.

    Redaction is applied to the fully formatted record (message plus any
    exception traceback), so secrets that surface inside stack traces are
    covered as well.
    """

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        rules: Iterable[tuple[re.Pattern[str], str]] | None = None,
    ):
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.rules = list(rules) if rules is not None else list(DEFAULT_REDACTION_RULES)

    def add_rule(self, pattern: str, replacement: str) -> None:
        """Append a custom redaction rule (for provider keys not covered by default)."""
        self.rules.append((re.compile(pattern), replacement))

    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        for pattern, replacement in self.rules:
            rendered = pattern.sub(replacement, rendered)
        return rendered


def build_formatter(fmt: str | None = None, redact_secrets: bool = True) -> logging.Formatter:
    """Return a :class:`RedactingFormatter` or a plain :class:`logging.Formatter`."""
    if redact_secrets:
        return RedactingFormatter(fmt=fmt)
    return logging.Formatter(fmt=fmt)


def setup_logging(
    level: str = "INFO",
    log_files: Iterable[str | object] | None = None,
    format_string: str | None = None,
    redact_secrets: bool = True,
    include_console: bool = False,
) -> None:
    """Configure the root logger with optional redaction and file handlers.

    Args:
        level: Root log level name (``DEBUG``, ``INFO``, ...).
        log_files: Paths to attach as ``FileHandler`` sinks.
        format_string: Overrides the default format.
        redact_secrets: Apply :class:`RedactingFormatter` to every handler.
        include_console: Also log to stderr. Off by default because the CLI
            renders its own rich console output.
    """
    fmt = format_string or "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    formatter = build_formatter(fmt=fmt, redact_secrets=redact_secrets)

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()

    handlers: list[logging.Handler] = []
    for path in log_files or []:
        handler = logging.FileHandler(str(path), encoding="utf-8", mode="a")
        handlers.append(handler)
    if include_console:
        handlers.append(logging.StreamHandler())

    for handler in handlers:
        handler.setFormatter(formatter)
        root.addHandler(handler)
