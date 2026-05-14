"""Obsidian Agent - A2A compliant specialist agent for Obsidian vault.

Implements all obsidian_* tools from the DUQ core as an A2A agent.
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from duq_agent_core import (
    AgentCapabilities,
    AgentCard,
    AgentConfig,
    AgentSkill,
    AgentTemplate,
    A2ATask,
    A2ATaskResult,
    ToolDefinition,
)
from obsidian_agent.service import ObsidianService, PathValidationError


class ObsidianAgent(AgentTemplate):
    """Obsidian specialist agent.

    Handles all Obsidian vault operations via A2A protocol.

    Args:
        config: Agent configuration
        vault_path: Path to the Obsidian vault
    """

    def __init__(self, config: AgentConfig, vault_path: str):
        self._service = ObsidianService(vault_path)
        self._vault_path = vault_path

        card = AgentCard(
            name="obsidian-agent",
            description="DUQ Obsidian vault specialist - manages notes, search, and navigation",
            url=config.get_public_url(),
            version="1.0.0",
            capabilities=AgentCapabilities(
                streaming=True,
                push_notifications=False,
                state_transition_history=True,
            ),
            skills=self._create_skills(),
        )

        super().__init__(card, config)

    def _create_skills(self) -> list[AgentSkill]:
        """Create skill definitions for agent card."""
        return [
            AgentSkill(
                id="obsidian_read",
                name="Read Note",
                description="Read a note from Obsidian vault",
                tags=["read", "note"],
                input_modes=["text"],
                output_modes=["text"],
            ),
            AgentSkill(
                id="obsidian_create",
                name="Create Note",
                description="Create a new note in Obsidian vault",
                tags=["write", "note", "create"],
                input_modes=["text"],
                output_modes=["text"],
            ),
            AgentSkill(
                id="obsidian_update",
                name="Update Note",
                description="Update an existing note (replace content)",
                tags=["write", "note", "update"],
                input_modes=["text"],
                output_modes=["text"],
            ),
            AgentSkill(
                id="obsidian_append",
                name="Append to Note",
                description="Append content to the end of an existing note",
                tags=["write", "note", "append"],
                input_modes=["text"],
                output_modes=["text"],
            ),
            AgentSkill(
                id="obsidian_delete",
                name="Delete Note",
                description="Delete a note from Obsidian vault",
                tags=["write", "note", "delete"],
                input_modes=["text"],
                output_modes=["text"],
            ),
            AgentSkill(
                id="obsidian_search",
                name="Search Notes",
                description="Search inside notes by text content",
                tags=["search", "grep"],
                input_modes=["text"],
                output_modes=["text"],
            ),
            AgentSkill(
                id="obsidian_move",
                name="Move Note",
                description="Move or rename a note",
                tags=["write", "note", "move", "rename"],
                input_modes=["text"],
                output_modes=["text"],
            ),
            AgentSkill(
                id="obsidian_folders",
                name="List Folders",
                description="Show folder structure in vault",
                tags=["list", "folders", "navigation"],
                input_modes=["text"],
                output_modes=["text"],
            ),
            AgentSkill(
                id="obsidian_list",
                name="List Notes",
                description="List all notes in vault or folder",
                tags=["list", "notes", "navigation"],
                input_modes=["text"],
                output_modes=["text"],
            ),
            AgentSkill(
                id="obsidian_tags",
                name="Get Tags",
                description="Get list of tags from a note",
                tags=["tags", "metadata"],
                input_modes=["text"],
                output_modes=["text"],
            ),
            AgentSkill(
                id="obsidian_search_tag",
                name="Search by Tag",
                description="Find all notes with a specific tag",
                tags=["search", "tags"],
                input_modes=["text"],
                output_modes=["text"],
            ),
            AgentSkill(
                id="obsidian_backlinks",
                name="Get Backlinks",
                description="Find all notes that link to a note",
                tags=["search", "links", "graph"],
                input_modes=["text"],
                output_modes=["text"],
            ),
        ]

    def get_tools(self) -> list[ToolDefinition]:
        """Return tool definitions for LLM function calling."""
        return [
            ToolDefinition(
                name="obsidian_read",
                description="Read a note. Need EXACT name.",
                input_schema={"path": {"type": "string", "required": True}},
            ),
            ToolDefinition(
                name="obsidian_create",
                description="Create a new note.",
                input_schema={
                    "path": {"type": "string", "required": True},
                    "content": {"type": "string", "required": True},
                    "overwrite": {"type": "boolean", "default": False},
                    "create_folders": {"type": "boolean", "default": False},
                },
            ),
            ToolDefinition(
                name="obsidian_update",
                description="Update existing note (replace content).",
                input_schema={
                    "path": {"type": "string", "required": True},
                    "content": {"type": "string", "required": True},
                },
            ),
            ToolDefinition(
                name="obsidian_append",
                description="Append content to existing note.",
                input_schema={
                    "path": {"type": "string", "required": True},
                    "content": {"type": "string", "required": True},
                },
            ),
            ToolDefinition(
                name="obsidian_delete",
                description="Delete a note. CAUTION: irreversible!",
                input_schema={"path": {"type": "string", "required": True}},
            ),
            ToolDefinition(
                name="obsidian_search",
                description="Search inside notes by text.",
                input_schema={
                    "query": {"type": "string", "required": True},
                    "folder": {"type": "string"},
                    "max_results": {"type": "integer", "default": 20},
                },
            ),
            ToolDefinition(
                name="obsidian_move",
                description="Move or rename a note.",
                input_schema={
                    "old_path": {"type": "string", "required": True},
                    "new_path": {"type": "string", "required": True},
                },
            ),
            ToolDefinition(
                name="obsidian_folders",
                description="Show folder structure in vault.",
                input_schema={},
            ),
            ToolDefinition(
                name="obsidian_list",
                description="List all notes in vault or folder.",
                input_schema={"folder": {"type": "string"}},
            ),
            ToolDefinition(
                name="obsidian_tags",
                description="Get tags from a note.",
                input_schema={"path": {"type": "string", "required": True}},
            ),
            ToolDefinition(
                name="obsidian_search_tag",
                description="Find notes with a specific tag.",
                input_schema={
                    "tag": {"type": "string", "required": True},
                    "folder": {"type": "string"},
                },
            ),
            ToolDefinition(
                name="obsidian_backlinks",
                description="Find notes that link to this note.",
                input_schema={"path": {"type": "string", "required": True}},
            ),
        ]

    async def process(self, task: A2ATask) -> A2ATaskResult:
        """Process an A2A task.

        Extracts skill ID and parameters from the task message/context
        and routes to the appropriate handler.

        Args:
            task: The A2A task to process

        Returns:
            Task result with status and data
        """
        logger.info(f"Processing task: {task.id}")
        logger.info(f"Task message: {task.message[:200] if task.message else 'None'}...")
        logger.info(f"Task context: {task.context}")

        try:
            # Extract skill and parameters from task
            skill_id = task.context.get("skill_id") or self._extract_skill_from_message(
                task.message
            )
            logger.info(f"Extracted skill_id: {skill_id}")
            params = task.context.get("parameters", {})

            # If no params provided, try to extract from message
            if not params and skill_id:
                params = self._extract_params_from_message(task.message, skill_id)

            # If no skill ID, treat message as a natural language request
            if not skill_id:
                return A2ATaskResult(
                    task_id=task.id,
                    status="failed",
                    error="No skill_id provided in task context. "
                    "Use context.skill_id to specify which operation to perform.",
                )

            # Route to handler
            handler = self._get_handler(skill_id)
            if not handler:
                return A2ATaskResult(
                    task_id=task.id,
                    status="failed",
                    error=f"Unknown skill: {skill_id}",
                )

            result = await handler(params)

            return A2ATaskResult(
                task_id=task.id,
                status="completed",
                result=result,
            )

        except Exception as e:
            logger.exception(f"Task processing failed: {task.id}")
            return A2ATaskResult(
                task_id=task.id,
                status="failed",
                error=str(e),
            )

    def _extract_skill_from_message(self, message: str | dict) -> str | None:
        """Try to extract skill ID from natural language message.

        Args:
            message: String message or A2A dict format (defensive handling)

        Returns:
            Skill ID or None if not found
        """
        # Handle dict message format (defensive, in case server doesn't extract)
        if isinstance(message, dict):
            parts = message.get("parts", [])
            if parts:
                text_parts = [
                    p.get("text", "") for p in parts
                    if isinstance(p, dict) and p.get("kind") == "text"
                ]
                message = " ".join(text_parts)
            elif "text" in message:
                message = str(message["text"])
            else:
                message = str(message)

        message_lower = message.lower()

        skill_keywords = {
            "obsidian_read": [
                "read", "get content", "show note", "open",
                "прочитай", "прочитать", "покажи", "открой", "содержимое",
            ],
            "obsidian_create": [
                "create", "new note", "write new",
                "создай", "создать", "новую заметку", "напиши",
            ],
            "obsidian_update": [
                "update", "replace", "change content",
                "обнови", "обновить", "замени", "измени",
            ],
            "obsidian_append": [
                "append", "add to", "add content",
                "добавь", "добавить", "дополни",
            ],
            "obsidian_delete": [
                "delete", "remove", "trash",
                "удали", "удалить", "убери",
            ],
            "obsidian_search": [
                "search", "find text", "grep", "search inside",
                "найди", "найти", "поиск", "поищи",
            ],
            "obsidian_move": [
                "move", "rename",
                "перемести", "переименуй",
            ],
            "obsidian_folders": [
                "folders", "folder structure", "list folders",
                "папки", "структура папок",
            ],
            "obsidian_list": [
                "list", "show notes", "what notes",
                "список", "покажи заметки", "какие заметки",
            ],
            "obsidian_tags": [
                "tags", "get tags",
                "теги", "покажи теги",
            ],
            "obsidian_search_tag": [
                "find by tag", "search tag", "notes with tag",
                "по тегу", "с тегом",
            ],
            "obsidian_backlinks": [
                "backlinks", "links to", "what links",
                "ссылки на", "обратные ссылки",
            ],
        }

        for skill_id, keywords in skill_keywords.items():
            if any(kw in message_lower for kw in keywords):
                return skill_id

        return None

    def _extract_params_from_message(
        self, message: str | dict, skill_id: str
    ) -> dict[str, Any]:
        """Extract parameters from natural language message.

        Simple heuristic extraction - looks for note names after keywords.

        Args:
            message: The message text
            skill_id: The detected skill ID

        Returns:
            Dict of extracted parameters
        """
        import re

        # Handle dict message format
        if isinstance(message, dict):
            parts = message.get("parts", [])
            if parts:
                text_parts = [
                    p.get("text", "") for p in parts
                    if isinstance(p, dict) and p.get("kind") == "text"
                ]
                message = " ".join(text_parts)
            elif "text" in message:
                message = str(message["text"])
            else:
                message = str(message)

        # For create - extract BOTH path and content
        if skill_id == "obsidian_create":
            result: dict[str, Any] = {}

            # Pattern: "заметку X с содержанием/содержимым/текстом Y"
            # Pattern: "note X with content Y"
            content_patterns = [
                r"(?:заметк[уа]|note|file)\s+([^\s]+)\s+(?:с\s+)?(?:содержани[ея]м?|содержимым|текстом|content|with)\s*[:\-]?\s*(.+)",
                r"(?:заметк[уа]|note|file)\s+([^\s]+)\s+[:]\s*(.+)",
            ]
            for pattern in content_patterns:
                match = re.search(pattern, message, re.IGNORECASE | re.DOTALL)
                if match:
                    path = match.group(1).strip().strip("'\".,!?;:")
                    content = match.group(2).strip().strip("'\"")
                    return {"path": path, "content": content}

            # Fallback: extract path only (will fail validation but provides better error)
            path_patterns = [
                r"(?:заметк[уа]|note|file|файл)\s+['\"]?([^\s'\"]+)['\"]?",
            ]
            for pattern in path_patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    path = match.group(1).strip().strip(".,!?;:'\"")
                    result["path"] = path
                    break

            return result

        # For read, update, append, delete - extract path only
        if skill_id in [
            "obsidian_read", "obsidian_update",
            "obsidian_append", "obsidian_delete", "obsidian_tags",
            "obsidian_backlinks",
        ]:
            # Try to find note name patterns
            # Match: "заметку X", "note X", "file X", etc.
            patterns = [
                r"(?:заметк[уа]|note|file|файл)\s+['\"]?([^\s'\"]+)['\"]?",
                r"(?:заметк[уа]|note|file|файл)\s+(.+?)(?:\s+и\s+|\s+потом\s+|$)",
            ]
            for pattern in patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    path = match.group(1).strip()
                    # Remove trailing punctuation
                    path = re.sub(r'[.,!?;:]+$', '', path)
                    return {"path": path}

            # Fallback: last word that looks like a path
            words = message.split()
            for word in reversed(words):
                if "/" in word or word.endswith(".md") or (
                    len(word) > 3 and "-" in word
                ):
                    return {"path": word.strip(".,!?;:'\"")}

        # For search - extract query
        if skill_id == "obsidian_search":
            # Extract text after "найди", "search", etc.
            patterns = [
                r"(?:найди|найти|search|find|искать)\s+(.+?)$",
                r"(?:поиск|grep)\s+(.+?)$",
            ]
            for pattern in patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    return {"query": match.group(1).strip()}

        # For list - extract folder
        if skill_id == "obsidian_list":
            patterns = [
                r"(?:в\s+папке|in folder|folder)\s+['\"]?([^\s'\"]+)['\"]?",
            ]
            for pattern in patterns:
                match = re.search(pattern, message, re.IGNORECASE)
                if match:
                    return {"folder": match.group(1).strip()}
            return {}  # List all

        return {}

    def _get_handler(self, skill_id: str):
        """Get handler function for a skill."""
        handlers = {
            "obsidian_read": self._handle_read,
            "obsidian_create": self._handle_create,
            "obsidian_update": self._handle_update,
            "obsidian_append": self._handle_append,
            "obsidian_delete": self._handle_delete,
            "obsidian_search": self._handle_search,
            "obsidian_move": self._handle_move,
            "obsidian_folders": self._handle_folders,
            "obsidian_list": self._handle_list,
            "obsidian_tags": self._handle_tags,
            "obsidian_search_tag": self._handle_search_tag,
            "obsidian_backlinks": self._handle_backlinks,
        }
        return handlers.get(skill_id)

    async def _handle_read(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle obsidian_read skill."""
        path = params.get("path", "")
        if not path:
            return {"error": "Path not specified"}

        note = await self._service.read_note(path)
        if note is None:
            return {"error": "Note not found"}

        return {"content": note.content, "path": note.path}

    async def _handle_create(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle obsidian_create skill."""
        path = params.get("path", "")
        content = params.get("content", "")
        overwrite = params.get("overwrite", False)
        create_folders = params.get("create_folders", False)

        if not path or not content:
            return {"error": "Need path and content"}

        result = await self._service.create_note(path, content, overwrite, create_folders)

        if isinstance(result, PathValidationError):
            return {
                "error": result.message,
                "similar_folders": result.similar_folders,
            }

        if result is None:
            return {"error": "Failed to create (may already exist)"}

        return {"success": True, "path": result.path}

    async def _handle_update(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle obsidian_update skill."""
        path = params.get("path", "")
        content = params.get("content", "")

        if not path or not content:
            return {"error": "Need path and content"}

        result = await self._service.update_note(path, content)

        if isinstance(result, PathValidationError):
            return {
                "error": result.message,
                "similar_notes": result.similar_folders,
            }

        if result is None:
            return {"error": "Failed to update"}

        return {"success": True, "path": result.path}

    async def _handle_append(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle obsidian_append skill."""
        path = params.get("path", "")
        content = params.get("content", "")

        if not path or not content:
            return {"error": "Need path and content"}

        note = await self._service.append_to_note(path, content)
        if note is None:
            return {"error": "Note not found"}

        return {"success": True, "path": note.path}

    async def _handle_delete(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle obsidian_delete skill."""
        path = params.get("path", "")
        if not path:
            return {"error": "Path not specified"}

        success = await self._service.delete_note(path)
        if not success:
            return {"error": "Note not found"}

        return {"success": True, "deleted": path}

    async def _handle_search(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle obsidian_search skill."""
        query = params.get("query", "")
        folder = params.get("folder")
        max_results = params.get("max_results", 20)

        if not query:
            return {"error": "Need query"}

        results = await self._service.search_notes(query, folder, max_results)
        if not results:
            return {"results": [], "message": f"Nothing found for '{query}'"}

        return {
            "results": [
                {
                    "path": r.path,
                    "name": r.name,
                    "folder": r.folder,
                    "matches": r.matches,
                }
                for r in results
            ],
            "count": len(results),
        }

    async def _handle_move(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle obsidian_move skill."""
        old_path = params.get("old_path", "")
        new_path = params.get("new_path", "")

        if not old_path or not new_path:
            return {"error": "Need old_path and new_path"}

        note = await self._service.move_note(old_path, new_path)
        if note is None:
            return {"error": "Failed to move (not found or target exists)"}

        return {"success": True, "old_path": old_path, "new_path": note.path}

    async def _handle_folders(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle obsidian_folders skill."""
        folders = await self._service.list_folders()
        return {"folders": folders, "count": len(folders)}

    async def _handle_list(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle obsidian_list skill."""
        folder = params.get("folder")
        notes = await self._service.list_notes(folder)
        return {"notes": notes, "count": len(notes)}

    async def _handle_tags(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle obsidian_tags skill."""
        path = params.get("path", "")
        if not path:
            return {"error": "Path not specified"}

        tags = await self._service.get_tags(path)
        return {"tags": tags, "count": len(tags)}

    async def _handle_search_tag(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle obsidian_search_tag skill."""
        tag = params.get("tag", "")
        folder = params.get("folder")

        if not tag:
            return {"error": "Tag not specified"}

        results = await self._service.search_by_tag(tag, folder)
        return {"results": results, "count": len(results)}

    async def _handle_backlinks(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle obsidian_backlinks skill."""
        path = params.get("path", "")
        if not path:
            return {"error": "Path not specified"}

        results = await self._service.get_backlinks(path)
        return {"backlinks": results, "count": len(results)}
