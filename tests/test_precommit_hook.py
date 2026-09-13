"""Test for pre-commit hook existence and basic functionality."""

import stat
from pathlib import Path


def _get_hook_path() -> Path:
    """Resolve the pre-commit hook path, falling back to canonical script in CI."""
    repo_root = Path(__file__).parent.parent
    git_hook = repo_root / ".git" / "hooks" / "pre-commit"
    if git_hook.exists():
        return git_hook
    script_hook = repo_root / "scripts" / "pre-commit.hook"
    if script_hook.exists():
        return script_hook
    return git_hook


def test_precommit_hook_exists():
    """Test that the pre-commit hook exists."""
    hook_path = _get_hook_path()
    assert hook_path.exists(), f"Pre-commit hook not found at {hook_path}"


def test_precommit_hook_is_executable():
    """Test that the pre-commit hook is executable."""
    hook_path = _get_hook_path()
    assert hook_path.exists(), f"Pre-commit hook not found at {hook_path}"

    mode = hook_path.stat().st_mode
    assert bool(mode & stat.S_IRUSR), f"Pre-commit hook is not readable: {hook_path}"
    assert bool(mode & (stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IROTH)), (
        f"Pre-commit hook has no access permissions: {hook_path}"
    )


def test_precommit_hook_content():
    """Test that the pre-commit hook has expected content."""
    hook_path = _get_hook_path()
    assert hook_path.exists(), f"Pre-commit hook not found at {hook_path}"
    content = hook_path.read_text(encoding="utf-8")

    assert "#!/usr/bin/env bash" in content, "Missing shebang"
    assert "check_sensitive_files.sh" in content, "Missing delegation to sensitive files checker"


if __name__ == "__main__":
    # Allow running directly for quick testing
    test_precommit_hook_exists()
    test_precommit_hook_is_executable()
    test_precommit_hook_content()
    print("All pre-commit hook tests passed!")
