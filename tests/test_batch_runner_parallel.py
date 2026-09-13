"""Tests for parallel batch processing functionality."""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from curiokraft_book.orchestrator.batch_runner import InteriorBatchRunner, RateLimiter
from curiokraft_book.orchestrator.state_manager import PageStatus


@pytest.fixture
def mock_manifest(tmp_path):
    """Create a minimal test manifest."""
    manifest = tmp_path / "test_manifest.json"
    manifest.write_text(
        """
    {
        "pages": [
            {"page_id": "P001", "page_number": 1, "canonical_object": "apple", "display_label": "Apple"},
            {"page_id": "P002", "page_number": 2, "canonical_object": "banana", "display_label": "Banana"},
            {"page_id": "P003", "page_number": 3, "canonical_object": "carrot", "display_label": "Carrot"},
            {"page_id": "P004", "page_number": 4, "canonical_object": "dog", "display_label": "Dog"}
        ]
    }
    """
    )
    return manifest


@pytest.fixture
def runner(mock_manifest, tmp_path):
    """Create a batch runner with mocked components."""
    runner = InteriorBatchRunner(
        manifest_path=mock_manifest,
        output_masters_dir=tmp_path / "masters",
        raw_generated_dir=tmp_path / "raw",
        inbox_dir=tmp_path / "inbox",
    )
    return runner


def test_rate_limiter_allows_requests_within_limit():
    """Verify rate limiter allows requests within the limit."""
    limiter = RateLimiter(requests_per_minute=10)

    start = time.time()
    for _ in range(5):  # Well under limit
        limiter.acquire()
    elapsed = time.time() - start

    # Should be very fast (no blocking)
    assert elapsed < 1.0


def test_rate_limiter_blocks_excess_requests():
    """Verify rate limiter blocks when exceeding limit."""
    limiter = RateLimiter(requests_per_minute=5)

    start = time.time()
    for _ in range(6):  # 6 requests with 5 RPM limit
        limiter.acquire()
    elapsed = time.time() - start

    # 6th request should be delayed (60s / 5 = 12s between requests)
    # Since we make 6 requests instantly, the last one waits ~12s
    assert elapsed >= 12.0


def test_rate_limiter_thread_safe():
    """Verify rate limiter works correctly with concurrent access."""
    from concurrent.futures import ThreadPoolExecutor

    limiter = RateLimiter(requests_per_minute=10)

    def acquire_token():
        limiter.acquire()
        return True

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(acquire_token) for _ in range(15)]
        results = [f.result() for f in futures]

    assert all(results)
    assert len(limiter.calls) <= 10  # Should respect limit


def test_generate_page_safe_success(runner, tmp_path):
    """Verify _generate_page_safe handles successful generation."""
    page = {
        "page_id": "P001",
        "page_number": 1,
        "canonical_object": "apple",
        "display_label": "Apple",
    }

    # Mock successful generation
    mock_path = tmp_path / "masters" / "page_001.png"
    mock_path.parent.mkdir(parents=True, exist_ok=True)
    mock_path.write_bytes(b"fake image")

    with patch.object(runner, "generate_single_page", return_value=mock_path):
        result = runner._generate_page_safe(page)

    assert result["success"] is True
    assert result["page_id"] == "P001"
    assert result["status"] == "APPROVED"
    assert "path" in result


def test_generate_page_safe_handles_failure(runner):
    """Verify _generate_page_safe handles generation failures gracefully."""
    page = {
        "page_id": "P002",
        "page_number": 2,
        "canonical_object": "banana",
        "display_label": "Banana",
    }

    # Mock failed generation
    with patch.object(runner, "generate_single_page", side_effect=ValueError("API error")):
        result = runner._generate_page_safe(page)

    assert result["success"] is False
    assert result["page_id"] == "P002"
    assert result["status"] == "FAILED"
    assert "API error" in result["error"]


def test_parallel_batch_runner_success(runner):
    """Verify parallel batch processing completes successfully."""
    # Mock successful generation for all pages
    mock_path = Path("/fake/page.png")

    with patch.object(runner, "generate_single_page", return_value=mock_path):
        report = runner.run_full_book_batch_parallel(max_workers=2)

    assert report.total_pages == 4
    assert report.successful_pages == 4
    assert report.failed_pages == 0
    assert len(report.page_records) == 4


def test_parallel_batch_handles_partial_failures(runner):
    """Verify parallel batch handles mixed success/failure scenarios."""

    def mock_generate(page_data, **kwargs):
        # Fail on page 2
        if page_data["page_id"] == "P002":
            raise ValueError("Simulated failure")
        return Path("/fake/page.png")

    with patch.object(runner, "generate_single_page", side_effect=mock_generate):
        report = runner.run_full_book_batch_parallel(max_workers=2)

    assert report.total_pages == 4
    assert report.successful_pages == 3
    assert report.failed_pages == 1

    # Verify failed page is recorded
    failed_records = [r for r in report.page_records if r["status"] == "FAILED"]
    assert len(failed_records) == 1
    assert failed_records[0]["page_id"] == "P002"


def test_parallel_batch_progress_callback(runner):
    """Verify progress callback is called correctly."""
    progress_calls = []

    def track_progress(current, total, label):
        progress_calls.append({"current": current, "total": total, "label": label})

    with patch.object(runner, "generate_single_page", return_value=Path("/fake/page.png")):
        runner.run_full_book_batch_parallel(
            max_workers=2, progress_callback=track_progress
        )

    # Should be called once per page
    assert len(progress_calls) == 4
    assert progress_calls[-1]["current"] == 4
    assert progress_calls[-1]["total"] == 4


def test_parallel_faster_than_sequential(runner):
    """Verify parallel processing is faster than sequential (integration test)."""

    def slow_generate(page_data, **kwargs):
        time.sleep(0.5)  # Simulate slow generation
        return Path("/fake/page.png")

    with patch.object(runner, "generate_single_page", side_effect=slow_generate):
        # Sequential timing
        start_seq = time.time()
        runner.run_full_book_batch()
        seq_time = time.time() - start_seq

        # Parallel timing
        start_par = time.time()
        runner.run_full_book_batch_parallel(max_workers=2)
        par_time = time.time() - start_par

    # Parallel should be at least 1.5x faster (ideally close to 2x)
    assert par_time < seq_time * 0.7


def test_thread_safe_state_updates(runner):
    """Verify state manager updates are thread-safe under concurrent load."""
    with patch.object(runner, "generate_single_page", return_value=Path("/fake/page.png")):
        report = runner.run_full_book_batch_parallel(max_workers=4)

    # Verify all pages were processed exactly once
    assert report.total_pages == 4
    page_ids = [r["page_id"] for r in report.page_records]
    assert len(page_ids) == len(set(page_ids))  # No duplicates

    # Verify state manager consistency
    state = runner.state_mgr.get_all_pages()
    assert len(state) >= 4  # At least 4 pages recorded


def test_parallel_batch_respects_worker_count(runner):
    """Verify parallel batch respects max_workers parameter."""
    call_times = []

    def track_timing(page_data, **kwargs):
        call_times.append(time.time())
        time.sleep(0.2)
        return Path("/fake/page.png")

    with patch.object(runner, "generate_single_page", side_effect=track_timing):
        runner.run_full_book_batch_parallel(max_workers=2)

    # With 2 workers and 4 pages (0.2s each), should take ~0.4s total
    # (2 batches of 2 pages processed in parallel)
    total_time = call_times[-1] - call_times[0]
    assert 0.3 < total_time < 0.6  # Allow some overhead


def test_parallel_batch_with_rate_limiting(runner):
    """Verify rate limiting is applied during parallel processing."""
    # Set very low rate limit for testing
    runner.rate_limiter = RateLimiter(requests_per_minute=10)

    with patch.object(runner, "generate_single_page", return_value=Path("/fake/page.png")):
        start = time.time()
        runner.run_full_book_batch_parallel(max_workers=2)
        elapsed = time.time() - start

    # With 10 RPM limit and 4 pages, should take at least some time
    # (not instant even with mocking)
    assert elapsed > 0.1


def test_parallel_batch_empty_manifest(tmp_path):
    """Verify parallel batch handles empty manifest gracefully."""
    empty_manifest = tmp_path / "empty.json"
    empty_manifest.write_text('{"pages": []}')

    runner = InteriorBatchRunner(
        manifest_path=empty_manifest,
        output_masters_dir=tmp_path / "masters",
        raw_generated_dir=tmp_path / "raw",
        inbox_dir=tmp_path / "inbox",
    )

    report = runner.run_full_book_batch_parallel(max_workers=4)

    assert report.total_pages == 0
    assert report.successful_pages == 0
    assert report.failed_pages == 0


def test_sequential_vs_parallel_output_identical(runner):
    """Verify parallel processing produces identical output to sequential."""

    def deterministic_generate(page_data, **kwargs):
        # Return predictable output based on page_id
        return Path(f"/fake/{page_data['page_id']}.png")

    with patch.object(runner, "generate_single_page", side_effect=deterministic_generate):
        seq_report = runner.run_full_book_batch()

        # Reset state
        runner.state_mgr = MagicMock()

        par_report = runner.run_full_book_batch_parallel(max_workers=2)

    # Same total success/failure counts
    assert seq_report.total_pages == par_report.total_pages
    assert seq_report.successful_pages == par_report.successful_pages
    assert seq_report.failed_pages == par_report.failed_pages

    # Same pages processed (order may differ)
    seq_ids = sorted([r["page_id"] for r in seq_report.page_records])
    par_ids = sorted([r["page_id"] for r in par_report.page_records])
    assert seq_ids == par_ids
