"""Tests for main module - entry point for Obsidian Agent."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from obsidian_agent.main import configure_logging, main


class TestConfigureLogging:
    """Tests for logging configuration."""

    def test_configure_logging_default(self) -> None:
        """Configure logging with default INFO level."""
        configure_logging()
        # No exception raised = success

    def test_configure_logging_debug(self) -> None:
        """Configure logging with DEBUG level."""
        configure_logging("DEBUG")
        # No exception raised = success

    def test_configure_logging_warning(self) -> None:
        """Configure logging with WARNING level."""
        configure_logging("WARNING")
        # No exception raised = success


class TestMain:
    """Tests for main entry point."""

    def test_main_exits_without_vault(self) -> None:
        """Main exits if vault path doesn't exist."""
        with patch.dict("os.environ", {"OBSIDIAN_VAULT_PATH": "/nonexistent/path"}):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_with_valid_vault(self) -> None:
        """Main starts agent with valid vault."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_vars = {
                "OBSIDIAN_VAULT_PATH": tmpdir,
                "OBSIDIAN_AGENT_PORT": "9001",
                "REDIS_URL": "redis://localhost:6379",
            }

            # Mock the agent's run method to avoid actually starting server
            with patch.dict("os.environ", env_vars):
                with patch("obsidian_agent.main.ObsidianAgent") as MockAgent:
                    mock_agent = MagicMock()
                    MockAgent.return_value = mock_agent

                    main()

                    MockAgent.assert_called_once()
                    mock_agent.run.assert_called_once()
