# Performance Profiling Guide

This document explains how to use the performance profiling tools in the CurioKraft Coloring Book Engine.

## Overview

The profiling system provides decorators and context managers to measure function
execution time, memory allocation, and throughput. Every timer is gated behind a
`logger.isEnabledFor(logging.INFO)` check, so when INFO logging is off the timer
costs a single level check and nothing else. That makes the decorators safe to
leave on production code paths.

`src/curiokraft_book/profiling.py` is the module. `scripts/profile_performance.py`
is the CLI front-end.

## Profiling Decorators

### Basic Profile Decorator

```python
from curiokraft_book.profiling import profile

@profile
def my_function():
    # Function implementation
    pass
```

Logs execution time at INFO level: `⏱️  module.function_name took 0.12s`

### Async Profile Decorator

```python
from curiokraft_book.profiling import profile_async

@profile_async
async def my_async_function():
    # Async function implementation
    pass
```

Logs execution time for async functions.

### Specialized Decorators

```python
from curiokraft_book.profiling import profile_batch_processing, profile_debate_round

@profile_batch_processing
def process_batch(page_count: int):
    # Reports pages/second when page_count is supplied
    pass

@profile_debate_round
def debate_round(round_num: int):
    # Includes the round number in the log line when supplied
    pass
```

`profile_batch_processing` looks for a `page_count` argument (keyword, positional
or an attribute on the bound instance) and appends a `(N pages/s)` figure.
`profile_debate_round` looks for a `round_num` argument so multi-round output is
distinguishable.

### Timer Context Manager

```python
from curiokraft_book.profiling import timer

def my_function():
    with timer("expensive operation"):
        # Code to time
        result = expensive_operation()
    return result
```

Logs: `⏱️  expensive operation took 0.45s`

### Memory Profiling

```python
from curiokraft_book.profiling import memory_profile

with memory_profile("Batch render"):
    render_all_pages()
```

Logs: `🧠 Batch render memory: retained=12.4MB, peak=88.1MB`

Backed by `tracemalloc`, so no third-party dependency. `retained` is the
allocation still live at the end of the block; `peak` is the high-water mark
inside it. A large `peak` with a small `retained` means a transient buffer (normal
for image work); `retained` growing across iterations points at a real leak.

### Benchmark Function

```python
from curiokraft_book.profiling import benchmark

# Run function multiple times and get statistics
stats = benchmark(my_function, iterations=5, arg1="value")
# Returns dict with avg_time, min_time, max_time, etc.
```

## Where Profiling Is Wired In

The batch entry points in `orchestrator/batch_runner.py` are wrapped with `timer`,
so a real run reports its own wall-clock time without any code changes:

```python
with timer("Full book batch (sequential)"):
    ...
with timer(f"Full book batch (parallel, {max_workers} workers)"):
    ...
```

The CLI configures logging at DEBUG (`cli.py`), so these lines are emitted by
default during a real run and land in `logs/pipeline.log`.

Other call sites are intentionally left undecorated — the profilers are cheap when
disabled but not free, and `generate_single_page()` runs 110 times per batch where
the aggregate per-page time is already visible from the batch-level timer.

## Profiling Script

```bash
# Module import cost (startup latency)
python scripts/profile_performance.py --target imports --iterations 3

# CLI construction cost
python scripts/profile_performance.py --target cli --iterations 3

# Orchestrator import cost
python scripts/profile_performance.py --target orchestrator --iterations 3

# Decorator overhead measurement
python scripts/profile_performance.py --target overhead

# Peak memory for a representative image workload
python scripts/profile_performance.py --target memory

# Everything except memory
python scripts/profile_performance.py --target all
```

## Measured Overhead

The table below is produced by `python scripts/profile_performance.py --target overhead`,
which times a trivial function 200,000 times undecorated, then decorated with INFO
disabled, then decorated with INFO enabled and the log record discarded (via a
`NullHandler`, so this isolates decorator cost from handler I/O).

Measured 2026-09-13, CPython 3.14.7 on Windows 10:

| Path | ns/call | Overhead vs. undecorated |
| --- | --- | --- |
| Undecorated function | 253 | — |
| `@profile`, INFO disabled | 1012 | **+759 ns** (~3.0×) |
| `@profile`, INFO enabled | 38,902 | +38.6 µs (~154×) |

**How to read this.** The disabled path is a single `logger.isEnabledFor(INFO)`
call plus the wrapper dispatch — it does not call `time.perf_counter()` at all.
When enabled, the cost is dominated by building and formatting the log record, not
by timing; the `NullHandler` figure is therefore a floor, and with a real file
handler the cost is higher.

Absolute nanoseconds are unreliable across machines — this host runs a bare Python
call at ~253 ns, roughly 4× slower than a typical laptop — so treat the **ratios**
as the portable figure and re-run the command on your own hardware if the
distinction matters.

The practical consequence: at ~0.8 µs per call, decorating a function called
1,000,000 times costs under a second when disabled. Decorating a hot inner loop is
still not advisable, but decorating per-page and per-batch entry points is free in
any human-scale sense.

To disable profiling output, keep the log level above INFO:

```bash
LOG_LEVEL=WARNING curiokraft-book generate book --parallel
```

## Integration with Py-Spy (Optional)

For deeper analysis that does not require code changes, use py-spy:

```bash
# Install py-spy (optional)
pip install py-spy

# Generate a flamegraph for batch processing
py-spy record -o profile.svg -- curiokraft-book generate book --parallel

# Live top view (like top for processes)
py-spy top --interval 0.1 -- curiokraft-book generate book --parallel
```

Py-spy samples the process from outside, so it works even for code paths that have
no `@profile` decorator.

## Best Practices

1. **Leave decorators in place** — the disabled cost is a fraction of a microsecond
2. **Focus on hotspots** — use profiling to find functions taking significant time, then optimise those
3. **Consider call frequency** — a function taking 10 ms but called 1000× matters more than one taking 100 ms called once
4. **Profile real workloads** — test with realistic data sizes (e.g. 10–20 page batches for quick feedback)
5. **Prefer py-spy for whole-run analysis** — it costs nothing at runtime and needs no code changes

## Interpreting Results

- **< 10 ms**: usually negligible unless called thousands of times
- **10–100 ms**: worth optimising if called frequently
- **> 100 ms**: high-priority optimisation target
- **Variance**: high variance between runs may indicate caching, network, or system effects

## Examples

### Timing a Batch Run

```python
# In cli.py or elsewhere
from curiokraft_book.profiling import timer

def generate_command():
    with timer("Full book generation"):
        runner = InteriorBatchRunner()
        result = runner.run_full_book_batch()
    return result
```

### Measuring Memory in the Rescue Pipeline

```python
from curiokraft_book.profiling import memory_profile

with memory_profile("Rescue + typography, 20 pages"):
    for page in pages[:20]:
        runner.generate_single_page(page)
```

A steadily rising `retained` figure across repeated runs is the signal to look for
leaked PIL images or open file handles; a high `peak` that returns to baseline is
normal.

---

*Last updated: 2026-09-13*
