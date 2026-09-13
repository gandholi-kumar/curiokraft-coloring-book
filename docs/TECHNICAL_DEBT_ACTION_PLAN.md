# Technical Debt & Improvements - Action Plan

**Created:** 2026-09-13  
**Status:** READY FOR EXECUTION  
**Total Estimated Effort:** 8-10 days  
**Expected Impact:** 4x performance improvement + enhanced security + reduced maintenance burden

---

## Quick Reference

| # | Item | Priority | Effort | Impact | Status |
|---|------|----------|--------|--------|--------|
| 1 | Parallel Batch Processing | HIGH | 2-3 days | 4x speedup | 🔴 Not Started |
| 2 | Fix Empty Except Blocks | HIGH | 1 hour | Better debugging | 🔴 Not Started |
| 3 | Extract DRY in Cover Generation | HIGH | 1-2 days | Easier maintenance | 🔴 Not Started |
| 4 | Add Pre-Commit Hook for KDP Forms | MEDIUM | 30 min | Enhanced privacy | 🔴 Not Started |
| 5 | Redact API Keys in Logs | MEDIUM | 2 hours | Enhanced security | 🔴 Not Started |
| 6 | Split ModelClient (ISP) | MEDIUM | 1 day | Better ISP adherence | 🔴 Not Started |
| 7 | Add Performance Profiling | LOW | 4 hours | Identify bottlenecks | 🔴 Not Started |
| 8 | Generate Architecture Diagrams | LOW | 4 hours | Better documentation | 🔴 Not Started |
| 9 | Add Integration Tests | LOW | 2 days | Higher confidence | 🔴 Not Started |
| 10 | Expand Unit Test Coverage | LOW | 2 days | 80% coverage target | 🔴 Not Started |

---

## High Priority Items (Complete First)

### 1. Add Parallel Batch Processing ⚡

**Priority:** HIGH  
**Effort:** 2-3 days  
**Impact:** 4x speedup (55 minutes → 14 minutes for 110-page batch)  
**Files to Modify:** `src/curiokraft_book/orchestrator/batch_runner.py`

#### Current State
```python
# Sequential processing in InteriorBatchRunner.run_full_book_batch()
for idx, page in enumerate(pages):
    self.generate_single_page(page)  # ~30 seconds per page
```

#### Implementation Steps

##### Step 1.1: Create Parallel Processing Method (2 hours)

**Location:** `src/curiokraft_book/orchestrator/batch_runner.py`

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import logging

class InteriorBatchRunner:
    def __init__(self, ...):
        # Existing code...
        self._state_lock = Lock()  # Thread-safe state updates
        
    def run_full_book_batch_parallel(
        self,
        max_workers: int = 4,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> dict[str, Any]:
        """
        Generate all pages in parallel using ThreadPoolExecutor.
        
        Args:
            max_workers: Number of parallel workers (default: 4)
            progress_callback: Optional callback for UI updates
            
        Returns:
            Summary dict with success/failure counts
            
        Note:
            - Respects LLM rate limits (4 workers = ~240 req/min)
            - Thread-safe state persistence via Lock
            - Graceful degradation on individual page failures
        """
        pages = self._load_and_filter_pages()
        total_count = len(pages)
        completed_count = 0
        failed_pages = []
        success_pages = []
        
        logger.info(f"Starting parallel batch: {total_count} pages, {max_workers} workers")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all page generation tasks
            future_to_page = {
                executor.submit(self._generate_page_safe, page): page
                for page in pages
            }
            
            # Process completed tasks as they finish
            for future in as_completed(future_to_page):
                page = future_to_page[future]
                page_id = page.get("page_id", "UNKNOWN")
                
                try:
                    result = future.result()
                    
                    if result.get("success"):
                        success_pages.append(page_id)
                        logger.info(f"✅ {page_id} completed")
                    else:
                        failed_pages.append(page_id)
                        logger.warning(f"⚠️ {page_id} failed: {result.get('error')}")
                        
                except Exception as e:
                    failed_pages.append(page_id)
                    logger.error(f"❌ {page_id} exception: {e}")
                
                completed_count += 1
                
                # Update progress callback (thread-safe)
                if progress_callback:
                    label = f"{page_id} ({completed_count}/{total_count})"
                    progress_callback(completed_count, total_count, label)
        
        return {
            "total": total_count,
            "success": len(success_pages),
            "failed": len(failed_pages),
            "failed_page_ids": failed_pages,
            "success_page_ids": success_pages,
        }
    
    def _generate_page_safe(self, page: dict) -> dict[str, Any]:
        """
        Thread-safe wrapper for single page generation.
        Handles exceptions and state persistence with lock.
        """
        page_id = page.get("page_id", "UNKNOWN")
        
        try:
            # Generate page (existing logic)
            result = self.generate_single_page(page)
            
            # Thread-safe state update
            with self._state_lock:
                if result.get("success"):
                    self.state_manager.update_status(page_id, PageStatus.APPROVED)
                else:
                    self.state_manager.update_status(page_id, PageStatus.FAILED)
            
            return {"success": True, "page_id": page_id, "result": result}
            
        except Exception as e:
            # Thread-safe error state update
            with self._state_lock:
                self.state_manager.update_status(page_id, PageStatus.FAILED)
                self.state_manager.add_error(page_id, str(e))
            
            return {"success": False, "page_id": page_id, "error": str(e)}
```

##### Step 1.2: Add CLI Flag for Parallel Mode (30 minutes)

**Location:** `src/curiokraft_book/cli.py`

```python
@app.command()
def generate(
    page_id: str | None = typer.Option(None, "--page", help="Generate single page"),
    batch: bool = typer.Option(False, "--batch", help="Generate all pages"),
    parallel: bool = typer.Option(False, "--parallel", help="Use parallel processing"),
    workers: int = typer.Option(4, "--workers", help="Parallel workers (default: 4)"),
):
    """Generate interior pages with optional parallel processing."""
    
    if batch:
        runner = InteriorBatchRunner()
        
        if parallel:
            console.print(f"[bold green]Starting parallel batch ({workers} workers)...[/]")
            result = runner.run_full_book_batch_parallel(max_workers=workers)
        else:
            console.print("[bold yellow]Starting sequential batch...[/]")
            result = runner.run_full_book_batch()
        
        # Display results
        console.print(f"\n✅ Success: {result['success']}/{result['total']}")
        if result['failed']:
            console.print(f"❌ Failed: {result['failed']} pages")
            for page_id in result['failed_page_ids']:
                console.print(f"  - {page_id}")
```

##### Step 1.3: Add Rate Limiting Safety (1 hour)

```python
import time
from collections import deque

class RateLimiter:
    """Token bucket rate limiter for LLM API calls."""
    
    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self.window_seconds = 60
        self.calls = deque()
    
    def acquire(self):
        """Block until a request slot is available."""
        now = time.time()
        
        # Remove calls outside the window
        while self.calls and self.calls[0] < now - self.window_seconds:
            self.calls.popleft()
        
        # If at limit, sleep until oldest call expires
        if len(self.calls) >= self.rpm:
            sleep_time = self.calls[0] + self.window_seconds - now + 0.1
            if sleep_time > 0:
                logger.debug(f"Rate limit reached, sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
                return self.acquire()  # Retry
        
        self.calls.append(now)

# Add to InteriorBatchRunner
class InteriorBatchRunner:
    def __init__(self, ...):
        # Existing code...
        self.rate_limiter = RateLimiter(requests_per_minute=60)
    
    def _generate_page_safe(self, page: dict) -> dict[str, Any]:
        # Acquire rate limit token before API call
        self.rate_limiter.acquire()
        
        # Rest of implementation...
```

##### Step 1.4: Write Tests (4 hours)

**Location:** `tests/test_batch_runner_parallel.py` (new file)

```python
"""Tests for parallel batch processing."""

import pytest
from unittest.mock import MagicMock, patch
from concurrent.futures import ThreadPoolExecutor

from curiokraft_book.orchestrator.batch_runner import InteriorBatchRunner


def test_parallel_batch_runner_success():
    """Verify parallel processing completes successfully."""
    runner = InteriorBatchRunner()
    runner._load_and_filter_pages = MagicMock(return_value=[
        {"page_id": "P001", "canonical_object": "apple"},
        {"page_id": "P002", "canonical_object": "banana"},
        {"page_id": "P003", "canonical_object": "carrot"},
    ])
    
    runner.generate_single_page = MagicMock(return_value={"success": True})
    
    result = runner.run_full_book_batch_parallel(max_workers=2)
    
    assert result["total"] == 3
    assert result["success"] == 3
    assert result["failed"] == 0
    assert runner.generate_single_page.call_count == 3


def test_parallel_batch_handles_failures():
    """Verify graceful handling of individual page failures."""
    runner = InteriorBatchRunner()
    runner._load_and_filter_pages = MagicMock(return_value=[
        {"page_id": "P001", "canonical_object": "apple"},
        {"page_id": "P002", "canonical_object": "banana"},  # Will fail
    ])
    
    def mock_generate(page):
        if page["page_id"] == "P002":
            raise ValueError("API error")
        return {"success": True}
    
    runner.generate_single_page = MagicMock(side_effect=mock_generate)
    
    result = runner.run_full_book_batch_parallel(max_workers=2)
    
    assert result["total"] == 2
    assert result["success"] == 1
    assert result["failed"] == 1
    assert "P002" in result["failed_page_ids"]


def test_rate_limiter_blocks_excess_requests():
    """Verify rate limiter enforces request limits."""
    from curiokraft_book.orchestrator.batch_runner import RateLimiter
    import time
    
    limiter = RateLimiter(requests_per_minute=5)
    
    start = time.time()
    for _ in range(6):  # 6 requests with limit of 5/min
        limiter.acquire()
    elapsed = time.time() - start
    
    # 6th request should be delayed
    assert elapsed >= 12.0  # 60s / 5 = 12s between requests


def test_thread_safe_state_updates():
    """Verify state manager updates are thread-safe."""
    runner = InteriorBatchRunner()
    runner._load_and_filter_pages = MagicMock(return_value=[
        {"page_id": f"P{i:03d}", "canonical_object": f"obj{i}"}
        for i in range(10)
    ])
    
    runner.generate_single_page = MagicMock(return_value={"success": True})
    
    # Run parallel batch
    result = runner.run_full_book_batch_parallel(max_workers=4)
    
    # Verify all state updates completed without corruption
    assert result["success"] == 10
    # Check state manager has no duplicate entries
    state = runner.state_manager.get_all_pages()
    assert len(state) == 10
```

#### Testing & Validation

```bash
# Run new tests
pytest tests/test_batch_runner_parallel.py -v

# Test sequential vs parallel performance
time curiokraft-book generate --batch
time curiokraft-book generate --batch --parallel --workers=4

# Verify state integrity after parallel run
curiokraft-book manifest show-state
```

#### Success Criteria
- ✅ 4x speedup on 110-page batch (55min → 14min)
- ✅ All tests passing
- ✅ Zero state corruption or race conditions
- ✅ Graceful handling of individual page failures
- ✅ Rate limiting prevents API throttling

#### Rollback Plan
If parallel processing introduces instability:
1. Keep sequential mode as default
2. Make `--parallel` opt-in flag
3. Add `--workers=1` fallback to disable parallelism

---

### 2. Fix Empty Except Blocks 🐛

**Priority:** HIGH  
**Effort:** 1 hour  
**Impact:** Better debugging and error visibility  
**Files to Modify:** `src/curiokraft_book/orchestrator/model_client.py`

#### Current Issues

**Location 1:** `model_client.py` (lines 22-23)
```python
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass  # ❌ Silent failure - no logging
```

**Location 2:** `model_client.py` (lines 40-42)
```python
try:
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass  # ❌ Silent failure - no logging
```

#### Implementation Steps

##### Step 2.1: Add Debug Logging (30 minutes)

```python
import logging
import sys

logger = logging.getLogger(__name__)

# Fix for stdout encoding
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    # Python < 3.7 doesn't have reconfigure()
    logger.debug("sys.stdout.reconfigure() not available (Python < 3.7)")
except Exception as e:
    # Other errors (e.g., unsupported terminal)
    logger.debug(f"Could not reconfigure stdout encoding to UTF-8: {e}")
    logger.debug("This is non-critical. Output may contain escaped characters.")

# Fix for stderr encoding
try:
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    logger.debug("sys.stderr.reconfigure() not available (Python < 3.7)")
except Exception as e:
    logger.debug(f"Could not reconfigure stderr encoding to UTF-8: {e}")
    logger.debug("This is non-critical. Error messages may contain escaped characters.")
```

##### Step 2.2: Write Test (15 minutes)

**Location:** `tests/test_model_client.py` (add to existing file)

```python
def test_encoding_reconfiguration_handles_errors(caplog):
    """Verify graceful handling when encoding reconfiguration fails."""
    import sys
    from unittest.mock import patch
    
    # Simulate reconfigure() failure
    with patch.object(sys.stdout, 'reconfigure', side_effect=Exception("Mock error")):
        # Re-import to trigger encoding setup
        import importlib
        import curiokraft_book.orchestrator.model_client as mc
        importlib.reload(mc)
    
    # Verify debug message was logged
    assert any("Could not reconfigure" in record.message for record in caplog.records)
```

##### Step 2.3: Update Documentation (15 minutes)

Add to `docs/DEVELOPMENT.md`:

```markdown
## Encoding Handling

The system attempts to configure UTF-8 encoding for stdout/stderr at startup.
If this fails (e.g., unsupported terminal, Python < 3.7), the system logs a
debug message and continues. This is non-critical - output may contain escaped
Unicode characters but functionality is unaffected.

To enable debug logging:
```bash
export LOG_LEVEL=DEBUG
curiokraft-book generate --page P001
```
```

#### Testing & Validation

```bash
# Run tests
pytest tests/test_model_client.py::test_encoding_reconfiguration_handles_errors -v

# Verify debug logs appear
LOG_LEVEL=DEBUG python -c "from curiokraft_book.orchestrator import model_client"
```

#### Success Criteria
- ✅ No more empty except blocks
- ✅ Debug logging captures failures
- ✅ Non-critical errors don't crash the system
- ✅ Test coverage for error paths

---

### 3. Extract DRY Violations in Cover Generation 🔧

**Priority:** HIGH  
**Effort:** 1-2 days  
**Impact:** Reduced maintenance burden, easier to extend  
**Files to Modify:** `src/curiokraft_book/orchestrator/debate_engine.py`

#### Current State

**Problem:** Front and back cover debate logic shares ~70% structure (~300 lines duplicated)

**Location:** `debate_engine.py` (lines 1566-1895)

```python
def run_cover_debate(self, cover_type: str) -> DebateResult:
    if cover_type == "back_cover":
        # 150 lines of back cover logic
        # Round 1: Layout specialist
        # Round 2: Typography specialist
        # Round 3: Brand specialist
        # Round 4: Judge synthesis
    else:  # front_cover
        # 150 lines of nearly identical front cover logic
        # Round 1: Layout specialist
        # Round 2: Typography specialist
        # Round 3: Brand specialist
        # Round 4: Judge synthesis
```

#### Implementation Steps

##### Step 3.1: Create Cover Debate Configuration Model (2 hours)

**Location:** `src/curiokraft_book/orchestrator/debate_engine.py`

```python
from dataclasses import dataclass
from typing import Callable

@dataclass
class CoverDebateConfig:
    """Configuration for cover debate orchestration."""
    cover_type: str  # "front_cover" or "back_cover"
    blueprint_spec: BlueprintLayoutSpec | None
    book_config: dict
    curriculum_config: dict
    
    # Agent prompts (different per cover type)
    layout_specialist_prompt: str
    typography_specialist_prompt: str
    brand_specialist_prompt: str
    judge_prompt: str
    
    # Validation rules (different per cover type)
    required_elements: list[str]
    forbidden_elements: list[str]
    
    @classmethod
    def from_cover_type(cls, cover_type: str, engine: "DebateEngine") -> "CoverDebateConfig":
        """Factory method to create config from cover type."""
        book_config = engine.book_config
        curriculum = engine.curriculum_config
        blueprint = engine._load_blueprint_for_cover(cover_type)
        
        if cover_type == "back_cover":
            return cls(
                cover_type="back_cover",
                blueprint_spec=blueprint,
                book_config=book_config,
                curriculum_config=curriculum,
                layout_specialist_prompt=cls._build_back_layout_prompt(blueprint, book_config),
                typography_specialist_prompt=cls._build_back_typography_prompt(book_config),
                brand_specialist_prompt=cls._build_back_brand_prompt(book_config),
                judge_prompt=cls._build_back_judge_prompt(),
                required_elements=["preview_cards", "feature_pills", "wave_baseline", "barcode_exclusion"],
                forbidden_elements=["front_mascot", "main_title"],
            )
        else:  # front_cover
            return cls(
                cover_type="front_cover",
                blueprint_spec=blueprint,
                book_config=book_config,
                curriculum_config=curriculum,
                layout_specialist_prompt=cls._build_front_layout_prompt(blueprint, book_config),
                typography_specialist_prompt=cls._build_front_typography_prompt(book_config),
                brand_specialist_prompt=cls._build_front_brand_prompt(book_config),
                judge_prompt=cls._build_front_judge_prompt(),
                required_elements=["mascot", "title", "subtitle", "volume_badge"],
                forbidden_elements=["barcode", "isbn"],
            )
    
    @staticmethod
    def _build_back_layout_prompt(blueprint, config) -> str:
        """Build Round 1 prompt for back cover layout specialist."""
        return f"""
        You are a KDP cover layout specialist for BACK COVERS.
        
        Canvas: {config['trim_width']}" × {config['trim_height']}" + bleed
        Blueprint: {blueprint.to_prompt_composition() if blueprint else "standard grid"}
        
        Design a back cover layout with:
        - Preview cards grid showing interior content
        - Feature callouts (age-appropriate benefits)
        - Baseline decorative wave
        - Barcode exclusion zone (2" × 1.2" bottom right)
        
        Requirements:
        - All text must be inside safe margins (0.5" from edges)
        - Cards must be evenly spaced and aligned
        - Colors: pastel tones matching curriculum
        """
    
    @staticmethod
    def _build_front_layout_prompt(blueprint, config) -> str:
        """Build Round 1 prompt for front cover layout specialist."""
        return f"""
        You are a KDP cover layout specialist for FRONT COVERS.
        
        Canvas: {config['trim_width']}" × {config['trim_height']}" + bleed
        Blueprint: {blueprint.to_prompt_composition() if blueprint else "standard mascot-centered"}
        
        Design a front cover layout with:
        - Large mascot character (friendly, engaging)
        - Title and subtitle (readable from thumbnails)
        - Volume badge (if series)
        - Decorative elements (age-appropriate)
        
        Requirements:
        - Mascot should occupy 40-50% of canvas
        - Title must be top 1/3, minimum 2" height
        - All text inside safe margins (0.5" from edges)
        """
    
    # Similar static methods for typography, brand, and judge prompts...
```

##### Step 3.2: Extract Common Debate Orchestration (4 hours)

```python
class DebateEngine:
    def run_cover_debate(self, cover_type: str) -> DebateResult:
        """
        Public API for cover debate. Delegates to common orchestration.
        """
        config = CoverDebateConfig.from_cover_type(cover_type, self)
        return self._run_cover_debate_common(config)
    
    def _run_cover_debate_common(self, config: CoverDebateConfig) -> DebateResult:
        """
        Common 4-round debate orchestration for both front and back covers.
        
        This eliminates ~150 lines of duplication between cover types.
        """
        logger.info(f"Starting {config.cover_type} debate with 4-round structure")
        
        rounds = []
        
        # ─────────────────────────────────────────────────────────────────
        # ROUND 1: Layout Specialist Proposal
        # ─────────────────────────────────────────────────────────────────
        r1_output = self.client.call_agent(
            agent_name="Layout Specialist",
            system_prompt=config.layout_specialist_prompt,
            user_prompt=f"Design the {config.cover_type} layout per specifications.",
            temperature=0.7,
        )
        
        rounds.append({
            "round": 1,
            "agent": "Layout Specialist",
            "output": r1_output.content,
        })
        
        # ─────────────────────────────────────────────────────────────────
        # ROUND 2: Typography Specialist Refinement
        # ─────────────────────────────────────────────────────────────────
        r2_output = self.client.call_agent(
            agent_name="Typography Specialist",
            system_prompt=config.typography_specialist_prompt,
            user_prompt=f"""
            Review the layout proposal:
            
            {r1_output.content}
            
            Refine typography, font sizes, and text placement for:
            - Thumbnail readability
            - Age-appropriate styling
            - Accessibility (dyslexia-friendly fonts)
            """,
            temperature=0.5,
        )
        
        rounds.append({
            "round": 2,
            "agent": "Typography Specialist",
            "output": r2_output.content,
        })
        
        # ─────────────────────────────────────────────────────────────────
        # ROUND 3: Brand Specialist Review
        # ─────────────────────────────────────────────────────────────────
        r3_output = self.client.call_agent(
            agent_name="Brand Specialist",
            system_prompt=config.brand_specialist_prompt,
            user_prompt=f"""
            Review layout and typography:
            
            LAYOUT: {r1_output.content}
            TYPOGRAPHY: {r2_output.content}
            
            Verify brand consistency:
            - Color palette matches curriculum
            - Mascot style consistent with interior
            - Parent messaging aligns with target audience
            """,
            temperature=0.3,
        )
        
        rounds.append({
            "round": 3,
            "agent": "Brand Specialist",
            "output": r3_output.content,
        })
        
        # ─────────────────────────────────────────────────────────────────
        # ROUND 4: Judge Synthesis & Prompt Lock
        # ─────────────────────────────────────────────────────────────────
        r4_output = self.client.call_agent(
            agent_name="Judge",
            system_prompt=config.judge_prompt,
            user_prompt=f"""
            Synthesize final {config.cover_type} prompt from 3 specialist reviews:
            
            ROUND 1 (Layout): {r1_output.content}
            ROUND 2 (Typography): {r2_output.content}
            ROUND 3 (Brand): {r3_output.content}
            
            Required elements: {', '.join(config.required_elements)}
            Forbidden elements: {', '.join(config.forbidden_elements)}
            
            Output JSON:
            {{
                "positive_prompt": "...",
                "negative_prompt": "...",
                "confidence_score": 0.95,
                "reasoning": "..."
            }}
            """,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        
        rounds.append({
            "round": 4,
            "agent": "Judge",
            "output": r4_output.content,
            "parsed_json": r4_output.parsed_json,
        })
        
        # Parse final prompt
        final_prompt = r4_output.parsed_json.get("positive_prompt", "")
        negative_prompt = r4_output.parsed_json.get("negative_prompt", "")
        
        return DebateResult(
            rounds=rounds,
            final_positive_prompt=final_prompt,
            final_negative_prompt=negative_prompt,
            metadata={
                "cover_type": config.cover_type,
                "confidence": r4_output.parsed_json.get("confidence_score"),
                "reasoning": r4_output.parsed_json.get("reasoning"),
            },
        )
```

##### Step 3.3: Write Tests (2 hours)

**Location:** `tests/test_debate_engine_refactor.py` (new file)

```python
"""Tests for refactored cover debate DRY extraction."""

import pytest
from unittest.mock import MagicMock

from curiokraft_book.orchestrator.debate_engine import (
    DebateEngine,
    CoverDebateConfig,
)


def test_cover_debate_config_from_back_cover():
    """Verify back cover config generation."""
    engine = DebateEngine()
    config = CoverDebateConfig.from_cover_type("back_cover", engine)
    
    assert config.cover_type == "back_cover"
    assert "preview_cards" in config.required_elements
    assert "barcode_exclusion" in config.required_elements
    assert "mascot" not in config.required_elements  # Front only


def test_cover_debate_config_from_front_cover():
    """Verify front cover config generation."""
    engine = DebateEngine()
    config = CoverDebateConfig.from_cover_type("front_cover", engine)
    
    assert config.cover_type == "front_cover"
    assert "mascot" in config.required_elements
    assert "title" in config.required_elements
    assert "barcode" in config.forbidden_elements  # Back only


def test_common_debate_orchestration():
    """Verify common debate logic works for both cover types."""
    engine = DebateEngine()
    engine.client = MagicMock()
    
    # Mock 4 rounds of agent responses
    engine.client.call_agent.side_effect = [
        MagicMock(content="Round 1: Layout"),
        MagicMock(content="Round 2: Typography"),
        MagicMock(content="Round 3: Brand"),
        MagicMock(
            content='{"positive_prompt": "final", "negative_prompt": "none"}',
            parsed_json={"positive_prompt": "final", "negative_prompt": "none"},
        ),
    ]
    
    result = engine.run_cover_debate("back_cover")
    
    assert len(result.rounds) == 4
    assert result.final_positive_prompt == "final"
    assert engine.client.call_agent.call_count == 4


def test_refactored_debate_matches_original_output():
    """Integration test: verify refactored version produces same output."""
    # This test would compare outputs from old vs new implementation
    # Keeping for regression testing during refactor
    pass
```

##### Step 3.4: Update Documentation (1 hour)

Update `docs/ARCHITECTURE_REVIEW_AND_ANALYSIS.md`:

```markdown
### 3.1.3 Cover Debate DRY Refactoring (2026-09-13)

**Problem:** Front and back cover debate logic shared ~70% structure (300 lines)

**Solution:** Extracted common orchestration to `_run_cover_debate_common()`:
- Created `CoverDebateConfig` dataclass for type-specific parameters
- Factory method `from_cover_type()` generates config
- Single orchestration method handles both cover types
- **Result:** Reduced from 300 lines to 150 lines (50% reduction)

**Extensibility:** Adding spine design or special edition covers now requires:
1. Add case to `CoverDebateConfig.from_cover_type()`
2. Define prompts and validation rules
3. Zero changes to orchestration logic
```

#### Testing & Validation

```bash
# Run all debate engine tests
pytest tests/test_debate_engine*.py -v

# Integration test: generate both covers
curiokraft-book cover --type back_cover
curiokraft-book cover --type front_cover

# Compare outputs with pre-refactor baseline
diff -u baseline/back_cover_debate.json generated/back_cover_debate.json
```

#### Success Criteria
- ✅ 50% reduction in duplicate code (300 → 150 lines)
- ✅ All existing tests passing
- ✅ Output identical to pre-refactor version
- ✅ Easier to add new cover types

#### Rollback Plan
Git revert commit if:
- Tests fail after refactor
- Output differs from baseline
- Performance degrades

---

## Medium Priority Items (Complete After High Priority)

### 4. Add Pre-Commit Hook for KDP Forms 🔒

**Priority:** MEDIUM  
**Effort:** 30 minutes  
**Impact:** Enhanced privacy protection  
**Files to Create:** `.git/hooks/pre-commit`

#### Implementation Steps

##### Step 4.1: Create Pre-Commit Hook (20 minutes)

**Location:** `.git/hooks/pre-commit` (new file)

```bash
#!/usr/bin/env bash
#
# Pre-commit hook to prevent accidental commit of sensitive KDP forms
#

set -e

# Color codes for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check for sensitive files in staging area
sensitive_patterns=(
    "inbox/kdp_forms/*.html"
    "inbox/kdp_forms/*.json"
    "*.env"
    "*_credentials.json"
    "*_api_key*"
)

found_sensitive=false

for pattern in "${sensitive_patterns[@]}"; do
    if git diff --cached --name-only | grep -qE "$pattern"; then
        if [ "$found_sensitive" = false ]; then
            echo -e "${RED}❌ ERROR: Attempting to commit sensitive files${NC}"
            echo ""
            found_sensitive=true
        fi
        
        echo -e "  ${YELLOW}Blocked:${NC} $pattern"
        git diff --cached --name-only | grep -E "$pattern" | sed 's/^/    - /'
    fi
done

if [ "$found_sensitive" = true ]; then
    echo ""
    echo -e "${YELLOW}Why this is blocked:${NC}"
    echo "  • KDP forms contain private publishing metadata"
    echo "  • Credentials and API keys must not be version controlled"
    echo ""
    echo -e "${YELLOW}To fix:${NC}"
    echo "  git reset HEAD <file>   # Unstage specific file"
    echo "  git reset HEAD .        # Unstage all files"
    echo ""
    echo -e "${YELLOW}To bypass this check (not recommended):${NC}"
    echo "  git commit --no-verify"
    echo ""
    exit 1
fi

# Check .gitignore coverage
if [ -f .gitignore ]; then
    if ! grep -q "inbox/kdp_forms/" .gitignore; then
        echo -e "${YELLOW}⚠️  Warning: inbox/kdp_forms/ not in .gitignore${NC}"
        echo "   Consider adding it for automatic protection"
    fi
fi

exit 0
```

##### Step 4.2: Make Hook Executable (1 minute)

```bash
chmod +x .git/hooks/pre-commit
```

##### Step 4.3: Add Hook Installation to Setup (5 minutes)

**Location:** `scripts/setup_dev_environment.sh` (new file)

```bash
#!/usr/bin/env bash
#
# Development environment setup script
#

echo "Setting up CurioKraft development environment..."

# Install pre-commit hooks
if [ -d .git ]; then
    echo "Installing pre-commit hooks..."
    cp hooks/pre-commit.template .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit
    echo "✅ Pre-commit hook installed"
else
    echo "⚠️  Not a git repository, skipping hook installation"
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -e ".[dev]"

# Run pre-commit autoupdate
if command -v pre-commit &> /dev/null; then
    echo "Updating pre-commit hooks..."
    pre-commit autoupdate
    pre-commit install
fi

echo "✅ Development environment ready"
```

##### Step 4.4: Document Hook Usage (4 minutes)

**Location:** `docs/DEVELOPMENT.md` (add section)

```markdown
## Pre-Commit Hooks

### Automatic Safety Checks

A pre-commit hook prevents accidental commits of:
- KDP form HTML files (`inbox/kdp_forms/*.html`)
- Environment files (`.env`)
- Credential files (`*_credentials.json`)
- API keys (`*_api_key*`)

### Installation

Hooks are installed automatically during setup:
```bash
./scripts/setup_dev_environment.sh
```

Manual installation:
```bash
cp hooks/pre-commit.template .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### Bypassing (Emergency Only)

In rare cases where you need to commit a file that triggers the hook:
```bash
git commit --no-verify -m "Emergency commit with justification"
```

**⚠️  Warning:** Only bypass if you understand the security implications.
```

#### Testing & Validation

```bash
# Test 1: Try to commit sensitive file (should fail)
touch inbox/kdp_forms/test_form.html
git add inbox/kdp_forms/test_form.html
git commit -m "Test commit"
# Expected: Hook blocks commit

# Test 2: Try to commit safe file (should succeed)
touch test_file.py
git add test_file.py
git commit -m "Safe commit"
# Expected: Commit succeeds

# Test 3: Verify bypass works
git commit --no-verify -m "Bypass test"
# Expected: Commit succeeds with warning

# Cleanup
git reset HEAD~1
rm test_file.py inbox/kdp_forms/test_form.html
```

#### Success Criteria
- ✅ Hook blocks sensitive file commits
- ✅ Hook allows normal commits
- ✅ Clear error messages with fix instructions
- ✅ Documented bypass procedure

---

### 5. Redact API Keys in Logs 🔐

**Priority:** MEDIUM  
**Effort:** 2 hours  
**Impact:** Enhanced security for debug logs  
**Files to Modify:** `src/curiokraft_book/cli.py`, new file `src/curiokraft_book/logging_config.py`

#### Implementation Steps

##### Step 5.1: Create Redacting Formatter (1 hour)

**Location:** `src/curiokraft_book/logging_config.py` (new file)

```python
"""Custom logging configuration with API key redaction."""

import logging
import re
from typing import Any


class RedactingFormatter(logging.Formatter):
    """
    Logging formatter that redacts sensitive information.
    
    Redacts:
    - API keys (various formats)
    - Bearer tokens
    - Passwords
    - Secret keys
    """
    
    # Compiled regex patterns for performance
    REDACTION_PATTERNS = [
        # OpenAI API keys: sk-...
        (re.compile(r'(sk-[a-zA-Z0-9]{32,})'), r'sk-***REDACTED***'),
        
        # Generic API key patterns
        (re.compile(r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_\-]{20,})(["\']?)', re.IGNORECASE),
         r'\1***REDACTED***\3'),
        
        # Gemini API keys: AIza...
        (re.compile(r'(AIza[a-zA-Z0-9_\-]{35})'), r'AIza***REDACTED***'),
        
        # Anthropic API keys
        (re.compile(r'(sk-ant-[a-zA-Z0-9_\-]{32,})'), r'sk-ant-***REDACTED***'),
        
        # Bearer tokens
        (re.compile(r'(Bearer\s+)([a-zA-Z0-9_\-\.]{20,})', re.IGNORECASE),
         r'\1***REDACTED***'),
        
        # Password fields
        (re.compile(r'(password["\']?\s*[:=]\s*["\']?)([^"\']+)(["\']?)', re.IGNORECASE),
         r'\1***REDACTED***\3'),
        
        # AWS keys
        (re.compile(r'(AKIA[0-9A-Z]{16})'), r'AKIA***REDACTED***'),
        
        # Generic secret patterns
        (re.compile(r'(secret["\']?\s*[:=]\s*["\']?)([^"\']+)(["\']?)', re.IGNORECASE),
         r'\1***REDACTED***\3'),
    ]
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with sensitive data redacted."""
        # Format the original message
        original = super().format(record)
        
        # Apply all redaction patterns
        redacted = original
        for pattern, replacement in self.REDACTION_PATTERNS:
            redacted = pattern.sub(replacement, redacted)
        
        return redacted
    
    @classmethod
    def add_pattern(cls, pattern: str, replacement: str):
        """
        Add custom redaction pattern at runtime.
        
        Args:
            pattern: Regex pattern to match
            replacement: Replacement string (can include capture groups)
        """
        cls.REDACTION_PATTERNS.append((re.compile(pattern), replacement))


def setup_logging(
    level: str = "INFO",
    format_string: str | None = None,
    redact_secrets: bool = True,
) -> None:
    """
    Configure application logging with optional redaction.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string (uses default if None)
        redact_secrets: Enable API key redaction (default: True)
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Create formatter
    if redact_secrets:
        formatter = RedactingFormatter(format_string)
    else:
        formatter = logging.Formatter(format_string)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler with formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Optionally add file handler
    if level == "DEBUG":
        file_handler = logging.FileHandler("debug.log", mode="a")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
```

##### Step 5.2: Integrate with CLI (30 minutes)

**Location:** `src/curiokraft_book/cli.py` (modify existing)

```python
# Add import at top
from curiokraft_book.logging_config import setup_logging

# Modify existing logging setup
def setup_cli_logging(verbose: bool = False):
    """Configure logging for CLI with API key redaction."""
    level = "DEBUG" if verbose else "INFO"
    
    # Use redacting formatter
    setup_logging(
        level=level,
        redact_secrets=True,  # Always redact in production
    )
    
    logger = logging.getLogger(__name__)
    logger.debug(f"Logging configured at {level} level with redaction enabled")

# Add global --verbose flag
@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
):
    """CurioKraft Coloring Book Generation CLI."""
    setup_cli_logging(verbose=verbose)
```

##### Step 5.3: Write Tests (30 minutes)

**Location:** `tests/test_logging_config.py` (new file)

```python
"""Tests for logging configuration and redaction."""

import logging
import pytest

from curiokraft_book.logging_config import RedactingFormatter, setup_logging


def test_redacting_formatter_openai_key():
    """Verify OpenAI API keys are redacted."""
    formatter = RedactingFormatter("%(message)s")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Using API key: sk-1234567890abcdefghijklmnopqrstuvwxyz",
        args=(),
        exc_info=None,
    )
    
    output = formatter.format(record)
    assert "sk-***REDACTED***" in output
    assert "sk-1234567890" not in output


def test_redacting_formatter_gemini_key():
    """Verify Gemini API keys are redacted."""
    formatter = RedactingFormatter("%(message)s")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Gemini key: AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ1234567",
        args=(),
        exc_info=None,
    )
    
    output = formatter.format(record)
    assert "AIza***REDACTED***" in output
    assert "AIzaSyABCDEF" not in output


def test_redacting_formatter_generic_api_key():
    """Verify generic API key patterns are redacted."""
    formatter = RedactingFormatter("%(message)s")
    
    test_cases = [
        'api_key="my_secret_key_12345678"',
        "api-key: super_secret_token",
        "apikey=another_api_key_value",
    ]
    
    for msg in test_cases:
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg=msg, args=(), exc_info=None,
        )
        output = formatter.format(record)
        assert "***REDACTED***" in output
        assert "secret" not in output.lower() or "***REDACTED***" in output


def test_redacting_formatter_bearer_token():
    """Verify Bearer tokens are redacted."""
    formatter = RedactingFormatter("%(message)s")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        args=(),
        exc_info=None,
    )
    
    output = formatter.format(record)
    assert "Bearer ***REDACTED***" in output
    assert "eyJhbGciOi" not in output


def test_redacting_formatter_password():
    """Verify passwords are redacted."""
    formatter = RedactingFormatter("%(message)s")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg='Connecting with password="my_super_secret_password"',
        args=(),
        exc_info=None,
    )
    
    output = formatter.format(record)
    assert "***REDACTED***" in output
    assert "my_super_secret_password" not in output


def test_redacting_formatter_preserves_safe_content():
    """Verify non-sensitive content is not modified."""
    formatter = RedactingFormatter("%(message)s")
    safe_messages = [
        "Starting batch generation for 110 pages",
        "Successfully generated page P001",
        "Validation passed: margins OK, grayscale OK",
    ]
    
    for msg in safe_messages:
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg=msg, args=(), exc_info=None,
        )
        output = formatter.format(record)
        assert output == msg  # Unchanged


def test_setup_logging_with_redaction(caplog):
    """Verify setup_logging enables redaction by default."""
    setup_logging(level="DEBUG", redact_secrets=True)
    
    logger = logging.getLogger("test_logger")
    logger.info("API key: sk-test_key_12345678901234567890")
    
    # Check captured logs
    assert any("***REDACTED***" in record.message for record in caplog.records)
    assert not any("sk-test_key_" in record.message for record in caplog.records)


def test_add_custom_pattern():
    """Verify custom redaction patterns can be added."""
    RedactingFormatter.add_pattern(
        r'(custom-secret-\w+)',
        r'custom-secret-***REDACTED***',
    )
    
    formatter = RedactingFormatter("%(message)s")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Using custom-secret-abc123",
        args=(),
        exc_info=None,
    )
    
    output = formatter.format(record)
    assert "custom-secret-***REDACTED***" in output
```

#### Testing & Validation

```bash
# Run tests
pytest tests/test_logging_config.py -v

# Manual test: verify redaction in CLI
curiokraft-book doctor --verbose 2>&1 | grep -i "api"
# Should see "***REDACTED***" instead of actual keys

# Test without redaction (for debugging only)
python -c "
from curiokraft_book.logging_config import setup_logging
import logging
setup_logging(level='DEBUG', redact_secrets=False)
logger = logging.getLogger('test')
logger.info('API key: sk-test123456789')
"
# Should show actual key (without redaction)
```

#### Success Criteria
- ✅ All API key formats redacted
- ✅ Bearer tokens redacted
- ✅ Passwords and secrets redacted
- ✅ Safe content unchanged
- ✅ Performance impact < 5%

---

### 6. Split ModelClient (ISP Violation) 🏗️

**Priority:** MEDIUM  
**Effort:** 1 day  
**Impact:** Better Interface Segregation Principle adherence  
**Files to Modify:** `src/curiokraft_book/orchestrator/model_client.py`, create new files

#### Current Problem

`ModelClient` serves multiple client types (violates ISP):
```python
class ModelClient:
    def call_agent(...)         # Text generation
    def call_vision(...)        # Image analysis
    def generate_illustration(...) # Image creation
```

#### Implementation Steps

##### Step 6.1: Create Separate Client Interfaces (3 hours)

**Location:** `src/curiokraft_book/orchestrator/llm_client.py` (new file)

```python
"""LLM client for text generation only."""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ModelResponse:
    """Standardized response from LLM."""
    content: str
    parsed_json: dict[str, Any] | None = None
    model_name: str = ""
    usage: dict[str, int] | None = None


class LLMClient:
    """
    Text generation client supporting multiple providers.
    
    Responsibilities:
    - Text generation via call_agent()
    - Provider auto-detection
    - Response normalization
    """
    
    def __init__(self, provider: str = "auto", model_name: str | None = None):
        self.provider = self._detect_provider(provider)
        self.model_name = model_name or self._default_model()
        logger.info(f"Initialized LLMClient with provider={self.provider}")
    
    def _detect_provider(self, preference: str) -> str:
        """Auto-detect available LLM provider."""
        # Implementation from original ModelClient...
        pass
    
    def call_agent(
        self,
        agent_name: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        response_format: dict | None = None,
    ) -> ModelResponse:
        """
        Generate text response from LLM.
        
        Args:
            agent_name: Identifier for logging/tracking
            system_prompt: System instructions
            user_prompt: User query
            temperature: Sampling temperature (0.0-1.0)
            response_format: Optional format spec (e.g., JSON)
        
        Returns:
            ModelResponse with generated text
        """
        if self.provider == "openai":
            return self._call_openai(...)
        elif self.provider == "anthropic":
            return self._call_anthropic(...)
        elif self.provider == "gemini":
            return self._call_gemini(...)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    # Provider-specific implementations...
```

**Location:** `src/curiokraft_book/orchestrator/vision_client.py` (new file)

```python
"""Vision client for image analysis only."""

import logging
from pathlib import Path
from PIL import Image

from .llm_client import ModelResponse

logger = logging.getLogger(__name__)


class VisionClient:
    """
    Image analysis client supporting vision-capable models.
    
    Responsibilities:
    - Image understanding via call_vision()
    - Multi-modal input handling
    - Structured output from images
    """
    
    def __init__(self, provider: str = "auto", model_name: str | None = None):
        self.provider = self._detect_vision_provider(provider)
        self.model_name = model_name or self._default_vision_model()
        logger.info(f"Initialized VisionClient with provider={self.provider}")
    
    def call_vision(
        self,
        image_path: Path | str,
        prompt: str,
        response_format: dict | None = None,
    ) -> ModelResponse:
        """
        Analyze image and generate structured response.
        
        Args:
            image_path: Path to image file
            prompt: Analysis instructions
            response_format: Optional format spec (e.g., JSON)
        
        Returns:
            ModelResponse with analysis results
        """
        img = Image.open(image_path)
        
        if self.provider == "gemini":
            return self._call_gemini_vision(img, prompt, response_format)
        elif self.provider == "openai":
            return self._call_openai_vision(img, prompt, response_format)
        else:
            raise ValueError(f"Provider {self.provider} doesn't support vision")
    
    # Provider-specific implementations...
```

**Location:** `src/curiokraft_book/orchestrator/image_generator.py` (new file)

```python
"""Image generation client."""

import logging
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)


class ImageGenerator:
    """
    Image generation client with pluggable providers.
    
    Responsibilities:
    - Image creation via generate()
    - Provider selection strategy
    - Inbox fallback logic
    """
    
    def __init__(self, provider: str = "auto"):
        self.provider = self._detect_image_provider(provider)
        logger.info(f"Initialized ImageGenerator with provider={self.provider}")
    
    def generate(
        self,
        positive_prompt: str,
        negative_prompt: str = "",
        width: int = 2550,
        height: int = 3300,
        source_mode: str = "auto",
    ) -> Image.Image:
        """
        Generate image from text prompt.
        
        Args:
            positive_prompt: What to include
            negative_prompt: What to avoid
            width: Canvas width in pixels
            height: Canvas height in pixels
            source_mode: "auto", "inbox", "api", "mock"
        
        Returns:
            PIL Image object
        """
        # Inbox check (if source_mode allows)
        if source_mode in ("auto", "inbox"):
            inbox_img = self._check_inbox(positive_prompt)
            if inbox_img:
                logger.info("Using image from inbox")
                return inbox_img
        
        # API generation
        if self.provider == "gemini":
            return self._generate_gemini(...)
        elif self.provider == "openai":
            return self._generate_openai(...)
        elif self.provider == "mock":
            return self._generate_mock(...)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    # Provider-specific implementations...
```

##### Step 6.2: Update Existing Code to Use New Clients (3 hours)

**Location:** `src/curiokraft_book/orchestrator/debate_engine.py`

```python
# OLD
from .model_client import ModelClient

class DebateEngine:
    def __init__(self, client: ModelClient | None = None):
        self.client = client or ModelClient()

# NEW
from .llm_client import LLMClient
from .image_generator import ImageGenerator

class DebateEngine:
    def __init__(
        self,
        llm_client: LLMClient | None = None,
        image_gen: ImageGenerator | None = None,
    ):
        self.llm = llm_client or LLMClient()
        self.image_gen = image_gen or ImageGenerator()
    
    def run_page_debate(self, page_record: dict):
        # Use self.llm instead of self.client
        r1_output = self.llm.call_agent(...)
```

**Location:** `src/curiokraft_book/orchestrator/batch_runner.py`

```python
# OLD
from .model_client import ModelClient

class InteriorBatchRunner:
    def __init__(self, model_client: ModelClient | None = None):
        self.client = model_client or ModelClient()

# NEW
from .llm_client import LLMClient
from .vision_client import VisionClient
from .image_generator import ImageGenerator

class InteriorBatchRunner:
    def __init__(
        self,
        llm_client: LLMClient | None = None,
        vision_client: VisionClient | None = None,
        image_gen: ImageGenerator | None = None,
    ):
        self.llm = llm_client or LLMClient()
        self.vision = vision_client or VisionClient()
        self.image_gen = image_gen or ImageGenerator()
```

##### Step 6.3: Add Backward Compatibility Facade (1 hour)

**Location:** `src/curiokraft_book/orchestrator/model_client.py` (modify)

```python
"""
Backward compatibility facade for ModelClient.

DEPRECATED: Use LLMClient, VisionClient, or ImageGenerator instead.
This facade will be removed in v2.0.
"""

import warnings
from .llm_client import LLMClient, ModelResponse
from .vision_client import VisionClient
from .image_generator import ImageGenerator


class ModelClient:
    """
    DEPRECATED: Unified client is deprecated.
    
    Use specific clients instead:
    - LLMClient for text generation
    - VisionClient for image analysis
    - ImageGenerator for image creation
    """
    
    def __init__(self, provider: str = "auto", model_name: str | None = None):
        warnings.warn(
            "ModelClient is deprecated. Use LLMClient, VisionClient, or ImageGenerator.",
            DeprecationWarning,
            stacklevel=2,
        )
        
        self.llm = LLMClient(provider, model_name)
        self.vision = VisionClient(provider, model_name)
        self.image_gen = ImageGenerator(provider)
        
        # Expose provider for backward compatibility
        self.provider = self.llm.provider
    
    def call_agent(self, *args, **kwargs) -> ModelResponse:
        """DEPRECATED: Use LLMClient.call_agent() instead."""
        return self.llm.call_agent(*args, **kwargs)
    
    def call_vision(self, *args, **kwargs) -> ModelResponse:
        """DEPRECATED: Use VisionClient.call_vision() instead."""
        return self.vision.call_vision(*args, **kwargs)
    
    def generate_illustration(self, *args, **kwargs):
        """DEPRECATED: Use ImageGenerator.generate() instead."""
        return self.image_gen.generate(*args, **kwargs)
```

##### Step 6.4: Write Tests (1 hour)

**Location:** `tests/test_client_split.py` (new file)

```python
"""Tests for ISP refactoring (split clients)."""

import pytest
from unittest.mock import MagicMock, patch

from curiokraft_book.orchestrator.llm_client import LLMClient
from curiokraft_book.orchestrator.vision_client import VisionClient
from curiokraft_book.orchestrator.image_generator import ImageGenerator


def test_llm_client_only_has_text_methods():
    """Verify LLMClient only exposes text generation."""
    client = LLMClient()
    
    assert hasattr(client, 'call_agent')
    assert not hasattr(client, 'call_vision')
    assert not hasattr(client, 'generate_illustration')


def test_vision_client_only_has_vision_methods():
    """Verify VisionClient only exposes image analysis."""
    client = VisionClient()
    
    assert hasattr(client, 'call_vision')
    assert not hasattr(client, 'call_agent')
    assert not hasattr(client, 'generate_illustration')


def test_image_generator_only_has_generation_methods():
    """Verify ImageGenerator only exposes image creation."""
    gen = ImageGenerator()
    
    assert hasattr(gen, 'generate')
    assert not hasattr(gen, 'call_agent')
    assert not hasattr(gen, 'call_vision')


def test_backward_compatibility_facade():
    """Verify ModelClient facade still works (with deprecation warning)."""
    from curiokraft_book.orchestrator.model_client import ModelClient
    
    with pytest.warns(DeprecationWarning, match="Use LLMClient"):
        client = ModelClient()
    
    assert hasattr(client, 'call_agent')
    assert hasattr(client, 'call_vision')
    assert hasattr(client, 'generate_illustration')
```

#### Testing & Validation

```bash
# Run tests
pytest tests/test_client_split.py -v

# Verify backward compatibility
pytest tests/test_model_client.py -v
# Should pass with deprecation warnings

# Integration test
curiokraft-book generate --page P001
# Should work without errors

# Check deprecation warnings
python -W all -m curiokraft_book.cli generate --page P001 2>&1 | grep -i deprecat
```

#### Success Criteria
- ✅ Clean separation: LLMClient, VisionClient, ImageGenerator
- ✅ Each client has single responsibility
- ✅ Backward compatibility maintained
- ✅ All existing tests passing
- ✅ Deprecation warnings guide migration

#### Migration Guide

Add to `docs/MIGRATION_V2.md`:

```markdown
## Migrating from ModelClient to Specific Clients

### Before (v1.x)
```python
from curiokraft_book.orchestrator.model_client import ModelClient

client = ModelClient()
text_response = client.call_agent(...)
vision_response = client.call_vision(...)
image = client.generate_illustration(...)
```

### After (v2.x)
```python
from curiokraft_book.orchestrator.llm_client import LLMClient
from curiokraft_book.orchestrator.vision_client import VisionClient
from curiokraft_book.orchestrator.image_generator import ImageGenerator

llm = LLMClient()
vision = VisionClient()
image_gen = ImageGenerator()

text_response = llm.call_agent(...)
vision_response = vision.call_vision(...)
image = image_gen.generate(...)
```

### Why?
- **Interface Segregation Principle**: Clients only expose relevant methods
- **Testability**: Mock only what you need
- **Clarity**: Clear separation of concerns
```

---

## Low Priority Items (Complete When Time Permits)

### 7. Add Performance Profiling 📊

**Priority:** LOW  
**Effort:** 4 hours  
**Impact:** Identify bottlenecks for optimization

#### Implementation Steps

##### Step 7.1: Add profiling decorator (1 hour)

```python
"""Performance profiling utilities."""

import functools
import time
import logging
from typing import Callable

logger = logging.getLogger(__name__)

def profile(func: Callable) -> Callable:
    """Decorator to profile function execution time."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info(f"⏱️  {func.__name__} took {elapsed:.2f}s")
        return result
    return wrapper
```

##### Step 7.2: Add py-spy integration (1 hour)

```bash
# Install py-spy
pip install py-spy

# Profile full batch generation
py-spy record -o profile.svg -- curiokraft-book generate --batch

# View flamegraph
open profile.svg
```

##### Step 7.3: Add memory profiling (1 hour)

```python
from memory_profiler import profile

@profile
def run_full_book_batch(self):
    # Existing implementation
    pass
```

##### Step 7.4: Create profiling documentation (1 hour)

Add to `docs/PERFORMANCE.md`:
- How to profile individual functions
- How to generate flamegraphs
- How to interpret results
- Known bottlenecks and mitigations

---

### 8. Generate Architecture Diagrams 📐

**Priority:** LOW  
**Effort:** 4 hours  
**Impact:** Better documentation and onboarding

#### Tools to Use
- **PlantUML** for class diagrams
- **Mermaid** for flowcharts
- **Graphviz** for dependency graphs

#### Diagrams to Create
1. **High-level architecture** - layers and components
2. **Multi-agent debate flow** - 4-round sequence diagram
3. **State machine** - page lifecycle transitions
4. **Class hierarchy** - providers, validators, compositors
5. **Data flow** - manifest → debate → generation → validation → PDF

---

### 9. Add Integration Tests 🧪

**Priority:** LOW  
**Effort:** 2 days  
**Impact:** Higher confidence in full pipeline

#### Test Cases
1. **Full single-page pipeline** - manifest → PDF
2. **Full batch pipeline** - 110 pages end-to-end
3. **Cover generation** - front + back + spine
4. **Rescue pipeline** - binarization + margin fitting
5. **KDP validation** - 18-point preflight
6. **State recovery** - crash and resume

---

### 10. Expand Unit Test Coverage 🎯

**Priority:** LOW  
**Effort:** 2 days  
**Impact:** 80% coverage target (currently 50%)

#### Areas Needing Coverage
- `orchestrator/debate_engine.py` - Currently ~30%
- `orchestrator/batch_runner.py` - Currently ~40%
- `compositor/cover.py` - Currently ~60%
- `validators/kdp_preflight.py` - Currently ~70%

#### Strategy
1. Write tests for untested functions
2. Add edge case tests
3. Add error path tests
4. Add property-based tests with Hypothesis

---

## Execution Timeline

### Week 1: High Priority Items
- **Day 1-3:** Parallel batch processing (#1)
- **Day 4:** Fix empty except blocks (#2)
- **Day 5:** Extract DRY violations (#3)

### Week 2: Medium Priority Items
- **Day 1:** Pre-commit hooks (#4) + API key redaction (#5)
- **Day 2-3:** Split ModelClient (#6)

### Week 3+: Low Priority (As Time Permits)
- Performance profiling (#7)
- Architecture diagrams (#8)
- Integration tests (#9)
- Expand test coverage (#10)

---

## Risk Management

### Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Parallel processing introduces race conditions | Medium | High | Extensive testing, thread-safe locks |
| Breaking changes during refactoring | Low | High | Backward compatibility facades |
| Performance regression | Low | Medium | Benchmark before/after |
| Test flakiness with parallelism | Medium | Low | Deterministic test data |

### Rollback Procedures

Each item should be implemented in a separate Git branch:
```bash
git checkout -b feature/parallel-batch-processing
# Implement, test, commit
git checkout main
git merge feature/parallel-batch-processing

# If issues arise:
git revert <commit-hash>
```

---

## Success Metrics

### Quantitative Targets
- ✅ **Performance:** 4x speedup (55min → 14min)
- ✅ **Code Quality:** 50% reduction in duplication
- ✅ **Test Coverage:** 50% → 80%
- ✅ **Security:** Zero API keys in logs
- ✅ **Maintainability:** ISP compliance

### Qualitative Goals
- ✅ Easier to add new volumes
- ✅ Easier to add new providers
- ✅ Better debugging experience
- ✅ Enhanced privacy protection
- ✅ Cleaner architecture

---

## Next Steps

1. **Review this action plan** with stakeholders
2. **Prioritize items** based on business needs
3. **Create GitHub issues** for each item
4. **Assign owners** for each task
5. **Set milestones** and deadlines
6. **Begin execution** with Week 1 high-priority items

**Ready to start implementation? 🚀**