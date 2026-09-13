"""Tests for the profiling module."""

import logging
import re
import time
from io import StringIO

from curiokraft_book.profiling import (
    benchmark,
    profile,
    profile_async,
    profile_batch_processing,
    profile_debate_round,
    timer,
)


def test_profile_decorator():
    """Test that the profile decorator logs execution time."""
    # Capture log output from the profiling module's logger
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    logger = logging.getLogger("curiokraft_book.profiling")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    @profile
    def test_function():
        time.sleep(0.01)  # 10ms
        return "success"

    # Execute function
    result = test_function()

    # Check result
    assert result == "success"

    # Check that logging occurred
    log_output = log_stream.getvalue()
    assert "test_function took" in log_output
    match = re.search(r"test_function took (\d+\.\d+)s", log_output)
    assert match is not None
    assert float(match.group(1)) > 0

    # Clean up handler
    logger.removeHandler(handler)


def test_profile_async_decorator():
    """Test that the profile_async decorator works."""
    import asyncio

    # Capture log output from the profiling module's logger
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    logger = logging.getLogger("curiokraft_book.profiling")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    @profile_async
    async def test_async_function():
        await asyncio.sleep(0.01)  # 10ms
        return "async_success"

    # Execute async function
    result = asyncio.run(test_async_function())

    # Check result
    assert result == "async_success"

    # Check that logging occurred
    log_output = log_stream.getvalue()
    assert "test_async_function took" in log_output

    # Clean up handler
    logger.removeHandler(handler)


def test_timer_context_manager():
    """Test that the timer context manager works."""
    # Capture log output from the profiling module's logger
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    logger = logging.getLogger("curiokraft_book.profiling")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    def test_function():
        with timer("test operation"):
            time.sleep(0.01)  # 10ms
        return "success"

    # Execute function
    result = test_function()

    # Check result
    assert result == "success"

    # Check that logging occurred
    log_output = log_stream.getvalue()
    assert "test operation took" in log_output
    match = re.search(r"test operation took (\d+\.\d+)s", log_output)
    assert match is not None
    assert float(match.group(1)) > 0

    # Clean up handler
    logger.removeHandler(handler)


def test_benchmark_function():
    """Test that the benchmark function works correctly."""

    def fast_function(x):
        return x * 2

    # Benchmark the function
    stats = benchmark(fast_function, iterations=5, x=5)

    # Check structure
    assert "func" in stats
    assert "iterations" in stats
    assert "total_time" in stats
    assert "avg_time" in stats
    assert "min_time" in stats
    assert "max_time" in stats
    assert "times" in stats
    assert "last_result" in stats

    # Check values
    assert stats["func"] == "fast_function"
    assert stats["iterations"] == 5
    assert stats["last_result"] == 10
    assert all(t >= 0 for t in stats["times"])
    assert stats["avg_time"] >= 0
    assert stats["min_time"] >= 0
    assert stats["max_time"] >= 0
    assert len(stats["times"]) == 5


def test_specialized_decorators():
    """Test the specialized profiling decorators."""
    # Capture log output from the profiling module's logger
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    logger = logging.getLogger("curiokraft_book.profiling")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    @profile_batch_processing
    def test_batch_function(page_count=None):
        time.sleep(0.01)  # 10ms
        return f"processed {page_count} pages"

    @profile_debate_round
    def test_debate_function(round_num=None):
        time.sleep(0.005)  # 5ms
        return f"debate round {round_num}"

    # Test batch processing decorator
    result1 = test_batch_function(page_count=10)
    assert result1 == "processed 10 pages"

    log_output = log_stream.getvalue()
    assert "test_batch_function processed 10 pages" in log_output
    match1 = re.search(r"in (\d+\.\d+)s", log_output)
    assert match1 is not None
    assert float(match1.group(1)) > 0

    # Reset log stream
    log_stream.seek(0)
    log_stream.truncate(0)

    # Test debate round decorator
    result2 = test_debate_function(round_num=2)
    assert result2 == "debate round 2"

    log_output = log_stream.getvalue()
    assert "test_debate_function debate round 2 took" in log_output
    match2 = re.search(r"took (\d+\.\d+)s", log_output)
    assert match2 is not None
    assert float(match2.group(1)) >= 0

    # Clean up handler
    logger.removeHandler(handler)


if __name__ == "__main__":
    # Allow running directly for quick testing
    import pytest

    pytest.main([__file__, "-v"])
