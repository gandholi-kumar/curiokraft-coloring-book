"""Performance profiling utilities for CurioKraft Coloring Book Engine.

This module provides decorators and context managers for profiling
function execution time, memory usage, and bottleneck identification.

All timers are gated behind an ``logger.isEnabledFor(logging.INFO)`` check so
that they cost essentially nothing when profiling is disabled (i.e. whenever
the effective log level is above INFO). This keeps the decorators safe to
leave on hot production code paths.
"""

import functools
import inspect
import logging
import time
import tracemalloc
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger(__name__)


def _is_profiling_enabled() -> bool:
    """Return True when INFO-level profiling output would actually be emitted."""
    return logger.isEnabledFor(logging.INFO)


def _format_bytes(num_bytes: int) -> str:
    """Render a byte count as a compact human-readable string."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024.0 or unit == "GB":
            return f"{size:.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}GB"


def _extract_argument(func: Callable, args: tuple, kwargs: dict, name: str) -> Any:
    """Best-effort lookup of a named argument from a call's positional/keyword args."""
    if name in kwargs:
        return kwargs[name]
    try:
        params = list(inspect.signature(func).parameters)
    except (TypeError, ValueError):
        return None
    if name in params:
        index = params.index(name)
        if index < len(args):
            return args[index]
    return None


def profile(func: Callable) -> Callable:
    """Decorator to profile function execution time.

    Args:
        func: Function to profile

    Returns:
        Wrapped function that logs execution time at INFO level.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not _is_profiling_enabled():
            return func(*args, **kwargs)
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info(f"⏱️  {func.__module__}.{func.__name__} took {elapsed:.2f}s")
        return result

    return wrapper


def profile_async(func: Callable) -> Callable:
    """Decorator to profile async function execution time.

    Args:
        func: Async function to profile

    Returns:
        Wrapped async function that logs execution time at INFO level.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if not _is_profiling_enabled():
            return await func(*args, **kwargs)
        start = time.perf_counter()
        result = await func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info(f"⏱️  {func.__module__}.{func.__name__} took {elapsed:.2f}s")
        return result

    return wrapper


@contextmanager
def timer(operation_name: str):
    """Context manager to time a block of code.

    Args:
        operation_name: Name of the operation being timed

    Example:
        with timer("PDF generation"):
            generate_pdf()
    """
    if not _is_profiling_enabled():
        yield
        return

    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.info(f"⏱️  {operation_name} took {elapsed:.2f}s")


@contextmanager
def memory_profile(operation_name: str):
    """Context manager to report peak memory allocation for a block of code.

    Uses :mod:`tracemalloc` so it works without any third-party dependency.
    Reports both the peak allocation and the delta between start and end, which
    is what identifies whether a block genuinely leaks memory or simply holds a
    large transient buffer.

    Args:
        operation_name: Name of the operation being measured

    Example:
        with memory_profile("Batch render"):
            render_all_pages()
    """
    if not _is_profiling_enabled():
        yield
        return

    tracemalloc.start()
    try:
        yield
    finally:
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        logger.info(
            f"🧠 {operation_name} memory: retained={_format_bytes(current)}, "
            f"peak={_format_bytes(peak)}"
        )


def benchmark(func: Callable, iterations: int = 1, *args, **kwargs) -> dict[str, Any]:
    """Benchmark a function over multiple iterations.

    Args:
        func: Function to benchmark
        iterations: Number of times to run the function
        *args, **kwargs: Arguments to pass to the function

    Returns:
        Dictionary with timing statistics
    """
    times = []

    for i in range(iterations):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        logger.debug(f"Iteration {i + 1}: {elapsed:.2f}s")

    return {
        "func": func.__name__,
        "iterations": iterations,
        "total_time": sum(times),
        "avg_time": sum(times) / len(times),
        "min_time": min(times),
        "max_time": max(times),
        "times": times,
        "last_result": result,
    }


# Convenience decorators for common profiling scenarios
def profile_batch_processing(func: Callable) -> Callable:
    """Specific decorator for batch processing functions.

    When the call supplies a ``page_count`` argument (or the bound instance
    exposes a ``page_count`` attribute) a throughput figure in pages/second is
    included in the log line.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not _is_profiling_enabled():
            return func(*args, **kwargs)

        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start

        page_count = kwargs.get("page_count")
        if page_count is None:
            page_count = _extract_argument(func, args, kwargs, "page_count")
        if page_count is None and args:
            page_count = getattr(args[0], "page_count", None)

        if page_count:
            rate = page_count / elapsed if elapsed > 0 else 0
            logger.info(
                f"⏱️  {func.__name__} processed {page_count} pages in "
                f"{elapsed:.2f}s ({rate:.1f} pages/s)"
            )
        else:
            logger.info(f"⏱️  {func.__name__} took {elapsed:.2f}s")
        return result

    return wrapper


def profile_debate_round(func: Callable) -> Callable:
    """Specific decorator for debate round functions.

    If the wrapped call receives a ``round_num`` argument it is included in the
    log line, so multi-round debates can be told apart in the transcript.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not _is_profiling_enabled():
            return func(*args, **kwargs)

        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start

        round_val = _extract_argument(func, args, kwargs, "round_num")
        if round_val is not None:
            logger.info(f"💬 {func.__name__} debate round {round_val} took {elapsed:.2f}s")
        else:
            logger.info(f"💬 {func.__name__} debate round took {elapsed:.2f}s")
        return result

    return wrapper
