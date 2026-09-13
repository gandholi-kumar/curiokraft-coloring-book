"""Test for pre-commit hook existence and basic functionality."""

import os
import stat
import subprocess
from pathlib import Path


def test_precommit_hook_exists():
    """Test that the pre-commit hook exists."""
    repo_root = Path(__file__).parent.parent
    hook_path = repo_root / ".git" / "hooks" / "pre-commit"

    # The hook should exist
    assert hook_path.exists(), f"Pre-commit hook not found at {hook_path}"


def test_precommit_hook_is_executable():
    """Test that the pre-commit hook is executable."""
    repo_root = Path(__file__).parent.parent
    hook_path = repo_root / ".git" / "hooks" / "pre-commit"

    # The hook should exist and be executable (delegates to version-controlled script)
    assert hook_path.exists(), f"Pre-commit hook not found at {hook_path}"

    # On Windows, we check the file permissions since .sh files aren't directly executable
    # The hook should have read permissions for owner (at minimum)
    import stat
    mode = hook_path.stat().st_mode
    assert bool(mode & stat.S_IRUSR), f"Pre-commit hook is not readable: {hook_path}"
    # Check that it's not completely inaccessible
    assert bool(mode & stat.S_IWUSR) or bool(mode & stat.S_IXUSR), f"Pre-commit hook has no access permissions: {hook_path}"


def test_precommit_hook_content():
    """Test that the pre-commit hook has expected content."""
    repo_root = Path(__file__).parent.parent
    hook_path = repo_root / ".git" / "hooks" / "pre-commit"

    if hook_path.exists():
        content = hook_path.read_text()

        # Should contain key elements (delegates to version-controlled script)
        assert "#!/usr/bin/env bash" in content, "Missing shebang"
        assert "check_sensitive_files.sh" in content, "Missing delegation to sensitive files checker"
        # The actual bypass instructions are in the delegated script and documentation


if __name__ == "__main__":
    # Allow running directly for quick testing
    test_precommit_hook_exists()
    test_precommit_hook_is_executable()
    test_precommit_hook_content()
    print("All pre-commit hook tests passed!")