"""Obsidian Agent - DUQ specialist for Obsidian vault management.

This agent handles all Obsidian-related operations via A2A protocol.
"""

from obsidian_agent.agent import ObsidianAgent
from obsidian_agent.service import ObsidianService

__version__ = "0.1.0"

__all__ = [
    "ObsidianAgent",
    "ObsidianService",
]
