"""Tests for ObsidianAgent - A2A compliant agent for Obsidian vault."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from duq_agent_core import AgentConfig, A2ATask, A2ATaskResult
from obsidian_agent.agent import ObsidianAgent
from obsidian_agent.service import Note, ObsidianService


@pytest.fixture
def agent_config() -> AgentConfig:
    """Create test agent configuration."""
    config = AgentConfig()
    config.port = 9001
    config.redis_url = "redis://localhost:6379"
    config.log_level = "DEBUG"
    return config


@pytest.fixture
def agent(temp_vault: Path, agent_config: AgentConfig) -> ObsidianAgent:
    """Create ObsidianAgent with temp vault."""
    return ObsidianAgent(config=agent_config, vault_path=str(temp_vault))


class TestAgentInit:
    """Tests for agent initialization."""

    def test_agent_creates_agent_card(self, agent: ObsidianAgent) -> None:
        """Agent creates valid agent card."""
        card = agent.card
        assert card.name == "obsidian-agent"
        assert "Obsidian" in card.description
        assert card.version == "1.0.0"

    def test_agent_has_capabilities(self, agent: ObsidianAgent) -> None:
        """Agent card has capabilities defined."""
        caps = agent.card.capabilities
        assert caps.streaming is True
        assert caps.state_transition_history is True

    def test_agent_has_skills(self, agent: ObsidianAgent) -> None:
        """Agent card has all required skills."""
        skills = agent.card.skills
        skill_ids = [s.id for s in skills]

        assert "obsidian_read" in skill_ids
        assert "obsidian_create" in skill_ids
        assert "obsidian_update" in skill_ids
        assert "obsidian_delete" in skill_ids
        assert "obsidian_search" in skill_ids
        assert "obsidian_move" in skill_ids
        assert "obsidian_folders" in skill_ids
        assert "obsidian_list" in skill_ids
        assert "obsidian_tags" in skill_ids
        assert "obsidian_search_tag" in skill_ids
        assert "obsidian_backlinks" in skill_ids

    def test_agent_has_12_skills(self, agent: ObsidianAgent) -> None:
        """Agent has exactly 12 skills defined."""
        assert len(agent.card.skills) == 12


class TestToolDefinitions:
    """Tests for tool definitions."""

    def test_get_tools_returns_list(self, agent: ObsidianAgent) -> None:
        """get_tools returns list of ToolDefinition."""
        tools = agent.get_tools()
        assert isinstance(tools, list)
        assert len(tools) == 12

    def test_tool_has_required_fields(self, agent: ObsidianAgent) -> None:
        """Each tool has name, description, parameters."""
        tools = agent.get_tools()
        for tool in tools:
            assert tool.name is not None
            assert tool.description is not None
            assert tool.parameters is not None

    def test_read_tool_definition(self, agent: ObsidianAgent) -> None:
        """obsidian_read tool has correct parameters."""
        tools = agent.get_tools()
        read_tool = next(t for t in tools if t.name == "obsidian_read")

        assert "path" in read_tool.parameters
        assert read_tool.parameters["path"]["required"] is True

    def test_create_tool_definition(self, agent: ObsidianAgent) -> None:
        """obsidian_create tool has correct parameters."""
        tools = agent.get_tools()
        create_tool = next(t for t in tools if t.name == "obsidian_create")

        assert "path" in create_tool.parameters
        assert "content" in create_tool.parameters
        assert "overwrite" in create_tool.parameters


class TestSkillExtraction:
    """Tests for extracting skill from natural language."""

    def test_extract_read_skill(self, agent: ObsidianAgent) -> None:
        """Extracts read skill from message."""
        result = agent._extract_skill_from_message("read the note about meetings")
        assert result == "obsidian_read"

    def test_extract_create_skill(self, agent: ObsidianAgent) -> None:
        """Extracts create skill from message."""
        result = agent._extract_skill_from_message("create a new note for today")
        assert result == "obsidian_create"

    def test_extract_search_skill(self, agent: ObsidianAgent) -> None:
        """Extracts search skill from message."""
        result = agent._extract_skill_from_message("search for project documentation")
        assert result == "obsidian_search"

    def test_extract_delete_skill(self, agent: ObsidianAgent) -> None:
        """Extracts delete skill from message."""
        result = agent._extract_skill_from_message("delete the old draft")
        assert result == "obsidian_delete"

    def test_extract_no_match(self, agent: ObsidianAgent) -> None:
        """Returns None when no skill matches."""
        result = agent._extract_skill_from_message("hello world")
        assert result is None


class TestHandlerRouting:
    """Tests for handler routing."""

    def test_get_handler_valid_skill(self, agent: ObsidianAgent) -> None:
        """Returns handler for valid skill ID."""
        handler = agent._get_handler("obsidian_read")
        assert handler is not None
        assert callable(handler)

    def test_get_handler_invalid_skill(self, agent: ObsidianAgent) -> None:
        """Returns None for invalid skill ID."""
        handler = agent._get_handler("invalid_skill")
        assert handler is None

    def test_all_skills_have_handlers(self, agent: ObsidianAgent) -> None:
        """All defined skills have handlers."""
        skill_ids = [
            "obsidian_read",
            "obsidian_create",
            "obsidian_update",
            "obsidian_append",
            "obsidian_delete",
            "obsidian_search",
            "obsidian_move",
            "obsidian_folders",
            "obsidian_list",
            "obsidian_tags",
            "obsidian_search_tag",
            "obsidian_backlinks",
        ]
        for skill_id in skill_ids:
            assert agent._get_handler(skill_id) is not None


class TestTaskProcessing:
    """Tests for A2A task processing."""

    @pytest.mark.asyncio
    async def test_process_read_task(self, agent: ObsidianAgent) -> None:
        """Process read task returns content."""
        task = A2ATask(
            id="task-1",
            message="Read README",
            context={"skill_id": "obsidian_read", "parameters": {"path": "README"}},
        )

        result = await agent.process(task)

        assert isinstance(result, A2ATaskResult)
        assert result.task_id == "task-1"
        assert result.status == "completed"
        assert "content" in result.result

    @pytest.mark.asyncio
    async def test_process_create_task(self, agent: ObsidianAgent) -> None:
        """Process create task creates note."""
        task = A2ATask(
            id="task-2",
            message="Create new note",
            context={
                "skill_id": "obsidian_create",
                "parameters": {"path": "new_test_note", "content": "Test content"},
            },
        )

        result = await agent.process(task)

        assert result.status == "completed"
        assert result.result["success"] is True

    @pytest.mark.asyncio
    async def test_process_without_skill_id(self, agent: ObsidianAgent) -> None:
        """Process task without skill_id returns error."""
        task = A2ATask(
            id="task-3",
            message="hello world",
            context={},
        )

        result = await agent.process(task)

        assert result.status == "failed"
        assert "No skill_id" in result.error

    @pytest.mark.asyncio
    async def test_process_unknown_skill(self, agent: ObsidianAgent) -> None:
        """Process task with unknown skill returns error."""
        task = A2ATask(
            id="task-4",
            message="Do something",
            context={"skill_id": "unknown_skill", "parameters": {}},
        )

        result = await agent.process(task)

        assert result.status == "failed"
        assert "Unknown skill" in result.error

    @pytest.mark.asyncio
    async def test_process_list_folders_task(self, agent: ObsidianAgent) -> None:
        """Process list folders task returns folders."""
        task = A2ATask(
            id="task-5",
            message="List folders",
            context={"skill_id": "obsidian_folders", "parameters": {}},
        )

        result = await agent.process(task)

        assert result.status == "completed"
        assert "folders" in result.result
        assert "Daily" in result.result["folders"]

    @pytest.mark.asyncio
    async def test_process_search_task(self, agent: ObsidianAgent) -> None:
        """Process search task finds matches."""
        task = A2ATask(
            id="task-6",
            message="Search vault",
            context={
                "skill_id": "obsidian_search",
                "parameters": {"query": "DUQ"},
            },
        )

        result = await agent.process(task)

        assert result.status == "completed"
        assert "results" in result.result


class TestHandlers:
    """Tests for individual handler methods."""

    @pytest.mark.asyncio
    async def test_handle_read_success(self, agent: ObsidianAgent) -> None:
        """Read handler returns note content."""
        result = await agent._handle_read({"path": "README"})
        assert "content" in result
        assert "My Vault" in result["content"]

    @pytest.mark.asyncio
    async def test_handle_read_not_found(self, agent: ObsidianAgent) -> None:
        """Read handler returns error for missing note."""
        result = await agent._handle_read({"path": "nonexistent"})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_handle_read_no_path(self, agent: ObsidianAgent) -> None:
        """Read handler returns error without path."""
        result = await agent._handle_read({})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_handle_create_success(self, agent: ObsidianAgent) -> None:
        """Create handler creates new note."""
        result = await agent._handle_create({
            "path": "handler_test_note",
            "content": "Handler test",
        })
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_handle_update_success(self, agent: ObsidianAgent) -> None:
        """Update handler updates existing note."""
        result = await agent._handle_update({
            "path": "README",
            "content": "Updated via handler",
        })
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_handle_append_success(self, agent: ObsidianAgent) -> None:
        """Append handler adds content to note."""
        result = await agent._handle_append({
            "path": "README",
            "content": "Appended via handler",
        })
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_handle_delete_success(self, agent: ObsidianAgent) -> None:
        """Delete handler removes note."""
        # First create a note to delete
        await agent._handle_create({
            "path": "to_delete",
            "content": "Will be deleted",
        })

        result = await agent._handle_delete({"path": "to_delete"})
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_handle_search_success(self, agent: ObsidianAgent) -> None:
        """Search handler finds matching notes."""
        result = await agent._handle_search({"query": "Project"})
        assert "results" in result

    @pytest.mark.asyncio
    async def test_handle_move_success(self, agent: ObsidianAgent) -> None:
        """Move handler moves note."""
        # Create note to move
        await agent._handle_create({
            "path": "to_move",
            "content": "Moving this",
        })

        result = await agent._handle_move({
            "old_path": "to_move",
            "new_path": "Archive/moved",
        })
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_handle_folders(self, agent: ObsidianAgent) -> None:
        """Folders handler returns folder list."""
        result = await agent._handle_folders({})
        assert "folders" in result
        assert "count" in result

    @pytest.mark.asyncio
    async def test_handle_list(self, agent: ObsidianAgent) -> None:
        """List handler returns note list."""
        result = await agent._handle_list({})
        assert "notes" in result
        assert "count" in result

    @pytest.mark.asyncio
    async def test_handle_tags(self, agent: ObsidianAgent) -> None:
        """Tags handler returns tags from note."""
        result = await agent._handle_tags({"path": "Daily/2026-05-10"})
        assert "tags" in result
        assert "daily" in result["tags"]

    @pytest.mark.asyncio
    async def test_handle_search_tag(self, agent: ObsidianAgent) -> None:
        """Search tag handler finds notes with tag."""
        result = await agent._handle_search_tag({"tag": "project"})
        assert "results" in result

    @pytest.mark.asyncio
    async def test_handle_backlinks(self, agent: ObsidianAgent) -> None:
        """Backlinks handler finds linking notes."""
        result = await agent._handle_backlinks({"path": "README"})
        assert "backlinks" in result
        assert "count" in result
