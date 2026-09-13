#!/usr/bin/env python3
"""Performance profiling script for CurioKraft Coloring Book Engine.

This script provides easy-to-use profiling commands for different parts of the system.

Targets:
    imports      - module import cost (startup latency)
    cli          - Typer app construction cost
    orchestrator - orchestrator module import cost
    overhead     - cost added by the profiling decorators themselves
    memory       - tracemalloc report for a representative workload
    all          - everything except ``memory`` (which is opt-in)
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Add src to path so we can import the package
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from curiokraft_book.profiling import (  # noqa: E402
    benchmark,
    memory_profile,
    profile,
    timer,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)

PROFILING_LOGGER = logging.getLogger("curiokraft_book.profiling")


def profile_imports():
    """Profile the time taken to import modules."""
    logger.info("Profiling module imports...")

    start = time.perf_counter()
    import curiokraft_book  # noqa: F401

    import_time = time.perf_counter() - start
    logger.info(f"⏱️  Imported curiokraft_book in {import_time:.2f}s")

    start = time.perf_counter()
    from curiokraft_book.cli import app  # noqa: F401

    cli_import_time = time.perf_counter() - start
    logger.info(f"⏱️  Imported CLI in {cli_import_time:.2f}s")

    return import_time + cli_import_time


def profile_cli_help():
    """Profile CLI help command setup."""
    logger.info("Profiling CLI setup...")

    with timer("CLI app construction"):
        from curiokraft_book.cli import app  # noqa: F401


def profile_orchestrator_imports():
    """Profile orchestrator module imports."""
    logger.info("Profiling orchestrator imports...")

    start = time.perf_counter()
    from curiokraft_book.orchestrator import batch_runner, debate_engine  # noqa: F401

    import_time = time.perf_counter() - start
    logger.info(f"⏱️  Imported orchestrator modules in {import_time:.2f}s")
    return import_time


def measure_decorator_overhead(iterations: int = 200_000) -> dict:
    """Measure the per-call cost the profiling decorators add.

    Runs the same trivial function three ways: undecorated, decorated with
    profiling disabled (level above INFO), and decorated with profiling
    enabled. The difference is the overhead the project claims in
    ``docs/PERFORMANCE.md``.
    """

    def trivial():
        return 1

    @profile
    def profiled():
        return 1

    def time_calls(fn, n):
        start = time.perf_counter()
        for _ in range(n):
            fn()
        return time.perf_counter() - start

    # Warm up so interpreter/JIT effects do not dominate the first measurement
    time_calls(trivial, 10_000)
    time_calls(profiled, 10_000)

    original_level = PROFILING_LOGGER.level
    try:
        # Disabled: INFO suppressed
        PROFILING_LOGGER.setLevel(logging.WARNING)
        disabled_total = time_calls(profiled, iterations)

        # Enabled but with logging output discarded, to isolate decorator cost
        # from handler I/O
        PROFILING_LOGGER.setLevel(logging.INFO)
        PROFILING_LOGGER.addHandler(logging.NullHandler())
        PROFILING_LOGGER.propagate = False
        enabled_total = time_calls(profiled, iterations)
    finally:
        PROFILING_LOGGER.setLevel(original_level)
        PROFILING_LOGGER.propagate = True

    baseline_total = time_calls(trivial, iterations)

    baseline_ns = baseline_total / iterations * 1e9
    disabled_ns = disabled_total / iterations * 1e9
    enabled_ns = enabled_total / iterations * 1e9

    results = {
        "iterations": iterations,
        "baseline_ns_per_call": baseline_ns,
        "disabled_ns_per_call": disabled_ns,
        "enabled_ns_per_call": enabled_ns,
        "disabled_overhead_ns": disabled_ns - baseline_ns,
        "enabled_overhead_ns": enabled_ns - baseline_ns,
        "disabled_overhead_pct": (disabled_ns - baseline_ns) / baseline_ns * 100,
        "enabled_overhead_pct": (enabled_ns - baseline_ns) / baseline_ns * 100,
    }

    logger.info("=" * 60)
    logger.info(f"DECORATOR OVERHEAD ({iterations:,} calls each)")
    logger.info("=" * 60)
    logger.info(f"  baseline (no decorator) : {baseline_ns:8.1f} ns/call")
    logger.info(
        f"  @profile, INFO disabled : {disabled_ns:8.1f} ns/call "
        f"(+{results['disabled_overhead_ns']:.1f} ns)"
    )
    logger.info(
        f"  @profile, INFO enabled  : {enabled_ns:8.1f} ns/call "
        f"(+{results['enabled_overhead_ns']:.1f} ns)"
    )
    return results


def measure_memory(operation_name: str = "synthetic 20-page canvas workload"):
    """Report peak allocation for a representative PIL workload.

    Emulates the per-page image work (allocate a 2550x3300 300-DPI grayscale
    canvas, resize, paste) without needing a generated book.
    """
    from PIL import Image

    with memory_profile(operation_name):
        canvases = []
        for _ in range(20):
            canvas = Image.new("L", (2550, 3300), 255)
            thumb = canvas.resize((2000, 2300), Image.Resampling.LANCZOS)
            canvases.append(thumb)
        # Simulate the per-page save/overwrite cycle
        while canvases:
            canvases.pop()


def main():
    parser = argparse.ArgumentParser(description="Profile CurioKraft performance")
    parser.add_argument(
        "--target",
        choices=["imports", "cli", "orchestrator", "overhead", "memory", "all"],
        default="all",
        help="What to profile",
    )
    parser.add_argument(
        "--iterations", type=int, default=3, help="Iterations for import benchmarks"
    )
    parser.add_argument(
        "--overhead-iterations",
        type=int,
        default=200_000,
        help="Iterations for the decorator overhead measurement",
    )
    args = parser.parse_args()

    logger.info("🚀 Starting CurioKraft performance profiling")
    logger.info("=" * 50)

    results = {}
    overhead = {}

    if args.target in ["imports", "all"]:
        results["imports"] = benchmark(profile_imports, iterations=args.iterations)

    if args.target in ["cli", "all"]:
        results["cli"] = benchmark(profile_cli_help, iterations=args.iterations)

    if args.target in ["orchestrator", "all"]:
        results["orchestrator"] = benchmark(profile_orchestrator_imports, iterations=args.iterations)

    if args.target in ["overhead", "all"]:
        overhead = measure_decorator_overhead(iterations=args.overhead_iterations)

    if args.target in ["memory", "all"]:
        measure_memory()

    logger.info("=" * 50)
    logger.info("📊 PROFILING RESULTS SUMMARY")
    logger.info("=" * 50)

    for target, result in results.items():
        logger.info(f"{target.upper()}:")
        logger.info(f"  Average time: {result['avg_time']:.2f}s")
        logger.info(f"  Min time: {result['min_time']:.2f}s")
        logger.info(f"  Max time: {result['max_time']:.2f}s")
        logger.info(f"  Total time: {result['total_time']:.2f}s")
        logger.info("")

    if overhead:
        logger.info("OVERHEAD:")
        logger.info(
            f"  Disabled: +{overhead['disabled_overhead_ns']:.1f} ns/call "
            f"({overhead['disabled_overhead_pct']:.1f}%)"
        )
        logger.info(
            f"  Enabled:  +{overhead['enabled_overhead_ns']:.1f} ns/call "
            f"({overhead['enabled_overhead_pct']:.1f}%)"
        )
        logger.info("")

    logger.info("✅ Profiling complete!")


if __name__ == "__main__":
    main()
