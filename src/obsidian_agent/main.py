"""Main entry point for Obsidian Agent.

Run with: python -m obsidian_agent.main
Or via CLI: obsidian-agent
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from loguru import logger

from duq_agent_core import AgentConfig
from obsidian_agent.agent import ObsidianAgent


def configure_logging(level: str = "INFO") -> None:
    """Configure loguru logging."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )


def main() -> None:
    """Main entry point."""
    # Load configuration from environment
    config = AgentConfig.from_env(prefix="OBSIDIAN_AGENT_")

    # Get vault path from environment or use default
    vault_path = os.getenv(
        "OBSIDIAN_VAULT_PATH",
        "/opt/obsidian-vault",
    )

    # Validate vault path
    if not Path(vault_path).exists():
        logger.error(f"Vault path does not exist: {vault_path}")
        logger.info("Set OBSIDIAN_VAULT_PATH environment variable")
        sys.exit(1)

    # Configure logging
    configure_logging(config.log_level)

    logger.info("Starting Obsidian Agent")
    logger.info(f"Vault path: {vault_path}")
    logger.info(f"Port: {config.port}")
    logger.info(f"Redis URL: {config.redis_url}")

    # Create and run agent
    agent = ObsidianAgent(config=config, vault_path=vault_path)
    agent.run()


if __name__ == "__main__":
    main()
