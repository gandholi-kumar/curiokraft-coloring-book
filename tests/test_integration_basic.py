"""Basic integration tests for CurioKraft Coloring Book Engine.

These tests verify that the core components work together correctly.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, patch



def test_cli_import_and_basic_structure():
    """Test that CLI can be imported and has expected structure."""
    from curiokraft_book.cli import app

    # Basic smoke test - app should exist
    assert app is not None
    assert hasattr(app, 'registered_groups')


def test_orchestrator_components_can_be_imported():
    """Test that orchestrator components can be imported together."""
    from curiokraft_book.orchestrator.batch_runner import InteriorBatchRunner
    from curiokraft_book.orchestrator.debate_engine import DebateEngine
    from curiokraft_book.orchestrator.llm_client import LLMClient
    from curiokraft_book.orchestrator.vision_client import VisionClient
    from curiokraft_book.orchestrator.image_generator import ImageGenerator

    # All imports should succeed
    assert InteriorBatchRunner is not None
    assert DebateEngine is not None
    assert LLMClient is not None
    assert VisionClient is not None
    assert ImageGenerator is not None


def test_model_client_facade_exists():
    """Test that the ModelClient facade still works for backward compatibility."""
    from curiokraft_book.orchestrator.model_client import ModelClient
    import warnings

    # Should be able to instantiate (with deprecation warning)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # Ignore deprecation warnings for this test
        client = ModelClient()

    # Should have the expected methods
    assert hasattr(client, 'call_agent')
    assert hasattr(client, 'call_vision')
    assert hasattr(client, 'generate_illustration')


def test_logging_configuration_works():
    """Test that logging configuration can be set up."""
    from curiokraft_book.logging_config import setup_logging, RedactingFormatter
    import logging

    # Should not raise an exception
    setup_logging(level="INFO", redact_secrets=True)

    # Should be able to get a logger and use it
    logger = logging.getLogger("test_logger")
    logger.info("Test message")

    # Test redacting formatter works
    formatter = RedactingFormatter("%(message)s")
    import logging
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="API key: sk-1234567890abcdefghijklmnopqrstuvwxyz",
        args=(), exc_info=None,
    )
    output = formatter.format(record)
    assert "***REDACTED***" in output
    assert "sk-1234567890" not in output


def test_profiling_module_can_be_used():
    """Test that the profiling module works correctly."""
    from curiokraft_book.profiling import profile, timer
    import time

    @profile
    def test_function():
        time.sleep(0.01)  # 10ms
        return "success"

    # Should execute and return expected value
    result = test_function()
    assert result == "success"

    # Timer context manager should work
    with timer("test operation"):
        time.sleep(0.01)  # 10ms

    # If we get here without exception, it works


def test_configuration_files_exist():
    """Test that expected configuration files exist in the repository."""
    import os
    repo_root = Path(__file__).parent.parent

    # Key config files should exist
    expected_files = [
        "config/book_config.yaml",
        "config/agents.yaml",
        "config/curriculum.yaml",
        "config/taxonomy.yaml",
        "manifest/pages.json",
        "manifest/objects.json",
        "pyproject.toml"
    ]

    for file_path in expected_files:
        full_path = repo_root / file_path
        assert full_path.exists(), f"Expected file {file_path} not found"


def test_source_structure_intact():
    """Test that the source code structure is as expected."""
    repo_root = Path(__file__).parent.parent
    src_root = repo_root / "src" / "curiokraft_book"

    # Key directories should exist
    expected_dirs = [
        "orchestrator",
        "compositor",
        "validators",
        "rescue"
    ]

    for dir_name in expected_dirs:
        dir_path = src_root / dir_name
        assert dir_path.exists() and dir_path.is_dir(), f"Expected directory {dir_name} not found"

    # Key modules should exist
    expected_modules = [
        "cli.py",
        "profiling.py",  # Our new module
        "logging_config.py"
    ]

    for module_name in expected_modules:
        module_path = src_root / module_name
        assert module_path.exists(), f"Expected module {module_name} not found"


if __name__ == "__main__":
    # Allow running directly for quick testing
    pytest.main([__file__, "-v"])