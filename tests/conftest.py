"""Pytest fixtures for obsidian-agent tests."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Generator

import pytest

from obsidian_agent.service import ObsidianService


@pytest.fixture
def temp_vault() -> Generator[Path, None, None]:
    """Create a temporary vault directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault = Path(tmpdir)

        # Create some folders
        (vault / "Daily").mkdir()
        (vault / "Projects").mkdir()
        (vault / "Projects" / "Work").mkdir()
        (vault / "Archive").mkdir()

        # Create some notes
        (vault / "README.md").write_text("# My Vault\n\nWelcome!")
        (vault / "Daily" / "2026-05-10.md").write_text(
            "# Daily Note\n\n#daily #log\n\nToday's tasks."
        )
        (vault / "Projects" / "duq.md").write_text(
            "# DUQ Project\n\n#project #ai\n\nLink to [[README]]"
        )
        (vault / "Projects" / "Work" / "meeting.md").write_text(
            "# Meeting Notes\n\n#work #meeting\n\nDiscussed [[duq]] project."
        )

        yield vault


@pytest.fixture
def service(temp_vault: Path) -> ObsidianService:
    """Create an ObsidianService instance with temp vault."""
    return ObsidianService(str(temp_vault))


@pytest.fixture
def empty_vault() -> Generator[Path, None, None]:
    """Create an empty vault for edge case testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
