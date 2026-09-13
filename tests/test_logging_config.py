"""Tests for API-key redaction in logging output (Item #5)."""

import logging

import pytest

from curiokraft_book.logging_config import (
    REDACTION_MARKER,
    RedactingFormatter,
    build_formatter,
    setup_logging,
)


def _format(message: str, formatter: logging.Formatter) -> str:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None,
    )
    return formatter.format(record)


@pytest.fixture
def formatter() -> RedactingFormatter:
    return RedactingFormatter("%(message)s")


# --- Provider-specific key formats -----------------------------------------


def test_redacts_openai_key(formatter):
    out = _format("Using OPENAI_API_KEY=sk-proj-AbCdEf0123456789AbCdEf0123456789", formatter)
    assert REDACTION_MARKER in out
    assert "AbCdEf0123456789" not in out


def test_redacts_anthropic_key(formatter):
    key = "sk-ant-api03-AbCdEf0123456789AbCdEf0123456789"
    out = _format(f"Anthropic key is {key}", formatter)
    assert "sk-ant-***REDACTED***" in out
    assert key not in out


def test_redacts_gemini_key(formatter):
    key = "AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q7"
    out = _format(f"provider key {key} rejected", formatter)
    assert "AIza***REDACTED***" in out
    assert key not in out


def test_redacts_gemini_key_in_env_assignment(formatter):
    """An api_key= prefix causes the whole value to be masked (also acceptable)."""
    key = "AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q7"
    out = _format(f"GEMINI_API_KEY={key}", formatter)
    assert REDACTION_MARKER in out
    assert key not in out
    assert "SyA1B2C3D4" not in out


def test_redacts_aws_access_key(formatter):
    out = _format("AWS access key AKIAIOSFODNN7EXAMPLE detected", formatter)
    assert "AKIA***REDACTED***" in out
    assert "IOSFODNN7EXAMPLE" not in out


def test_redacts_huggingface_token(formatter):
    out = _format("hf_AbCdEf0123456789AbCdEf0123456789 used for download", formatter)
    assert "hf_***REDACTED***" in out


# --- Generic credential shapes ----------------------------------------------


def test_redacts_bearer_token(formatter):
    out = _format("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", formatter)
    assert f"Bearer {REDACTION_MARKER}" in out
    assert "eyJhbGciOi" not in out


def test_redacts_x_goog_api_key_header(formatter):
    out = _format("headers: {'x-goog-api-key': 'AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q7'}", formatter)
    assert "AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q7" not in out


@pytest.mark.parametrize(
    "message",
    [
        'api_key="my_secret_value_12345678"',
        "api-key: super_secret_token_value",
        "apikey=another_api_key_value_here",
    ],
)
def test_redacts_generic_api_key_forms(formatter, message):
    out = _format(message, formatter)
    assert REDACTION_MARKER in out
    assert "secret" not in out


def test_redacts_password_and_secret(formatter):
    out = _format('Connecting with password="hunter2hunter2" and secret=abc123def456', formatter)
    assert out.count(REDACTION_MARKER) == 2
    assert "hunter2hunter2" not in out
    assert "abc123def456" not in out


def test_redacts_url_embedded_credentials(formatter):
    out = _format("Fetching https://user:s3cr3tpass@example.com/data", formatter)
    assert "s3cr3tpass" not in out
    assert "https://user:***REDACTED***@example.com/data" in out


# --- Tracebacks -------------------------------------------------------------


def test_redacts_keys_in_exception_traceback(formatter):
    import sys

    try:
        raise ValueError("auth failed for key sk-proj-AbCdEf0123456789AbCdEf0123456789")
    except ValueError:
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="generation failed",
            args=(),
            exc_info=sys.exc_info(),
        )
    out = formatter.format(record)
    assert "AbCdEf0123456789" not in out
    assert REDACTION_MARKER in out
    # Traceback structure is preserved
    assert "Traceback" in out


# --- Non-regression ---------------------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        "Starting batch generation for 110 pages",
        "Successfully generated page P001 (APPLE)",
        "Validation passed: margins OK, grayscale OK, dimensions OK",
        "Resolver picked 13 alphabet cards for section 'a_to_m'",
    ],
)
def test_safe_messages_unchanged(formatter, message):
    assert _format(message, formatter) == message


def test_redaction_does_not_mangle_short_identifiers(formatter):
    """Words like 'token' in prose must not swallow the rest of the sentence."""
    out = _format("Token bucket refilled; 42 tokens available", formatter)
    assert "42 tokens available" in out


# --- Formatter / setup wiring ----------------------------------------------


def test_build_formatter_respects_redact_flag():
    assert isinstance(build_formatter(redact_secrets=True), RedactingFormatter)
    assert not isinstance(build_formatter(redact_secrets=False), RedactingFormatter)


def test_add_custom_rule(formatter):
    formatter.add_rule(r"acme-[a-z0-9]{10}", "acme-***REDACTED***")
    out = _format("key acme-abcdefghij in use", formatter)
    assert "acme-***REDACTED***" in out


def test_setup_logging_handlers_use_redacting_formatter(tmp_path):
    log_file = tmp_path / "test.log"
    setup_logging(level="INFO", log_files=[log_file], redact_secrets=True)

    logging.getLogger("curiokraft.test").warning(
        "provider rejected key sk-proj-AbCdEf0123456789AbCdEf0123456789"
    )
    for handler in logging.getLogger().handlers:
        handler.flush()

    contents = log_file.read_text(encoding="utf-8")
    assert REDACTION_MARKER in contents
    assert "AbCdEf0123456789" not in contents
