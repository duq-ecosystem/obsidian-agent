"""Obsidian Service - File operations for Obsidian vault.

Handles all file I/O operations for the Obsidian vault.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os
from loguru import logger


@dataclass
class Note:
    """Represents an Obsidian note."""

    path: str
    name: str
    folder: str
    content: str


@dataclass
class SearchResult:
    """Search result with matches."""

    path: str
    name: str
    folder: str
    matches: list[dict[str, Any]]


@dataclass
class PathValidationError:
    """Error when path validation fails."""

    message: str
    similar_folders: list[str]


class ObsidianService:
    """Service for Obsidian vault file operations.

    Args:
        vault_path: Path to the Obsidian vault root
    """

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path).resolve()

        if not self.vault_path.exists():
            raise ValueError(f"Vault path does not exist: {vault_path}")

    def _resolve_path(self, relative_path: str) -> Path:
        """Resolve relative path to absolute, ensuring it's within vault."""
        # Normalize path
        clean_path = relative_path.lstrip("/")

        # Add .md extension if missing
        if not clean_path.endswith(".md"):
            clean_path += ".md"

        full_path = (self.vault_path / clean_path).resolve()

        # Security check: ensure path is within vault
        if not str(full_path).startswith(str(self.vault_path)):
            raise ValueError(f"Path escapes vault: {relative_path}")

        return full_path

    def _get_relative_path(self, full_path: Path) -> tuple[str, str]:
        """Get folder and name from full path."""
        rel_path = full_path.relative_to(self.vault_path)
        folder = str(rel_path.parent) if rel_path.parent != Path(".") else ""
        name = rel_path.name
        return folder, name

    async def read_note(self, path: str) -> Note | None:
        """Read a note from the vault.

        Args:
            path: Relative path to the note

        Returns:
            Note object or None if not found
        """
        try:
            full_path = self._resolve_path(path)

            if not full_path.exists():
                return None

            async with aiofiles.open(full_path, "r", encoding="utf-8") as f:
                content = await f.read()

            folder, name = self._get_relative_path(full_path)
            return Note(
                path=str(full_path.relative_to(self.vault_path)),
                name=name,
                folder=folder,
                content=content,
            )

        except Exception as e:
            logger.error(f"Error reading note: {e}")
            return None

    async def create_note(
        self,
        path: str,
        content: str,
        overwrite: bool = False,
        create_folders: bool = False,
    ) -> Note | PathValidationError | None:
        """Create a new note.

        Args:
            path: Relative path for the note
            content: Note content
            overwrite: If True, overwrite existing note
            create_folders: If True, create missing folders

        Returns:
            Note object, PathValidationError if folder doesn't exist, or None on failure
        """
        try:
            full_path = self._resolve_path(path)

            # Check if folder exists
            if not full_path.parent.exists():
                if create_folders:
                    await aiofiles.os.makedirs(full_path.parent, exist_ok=True)
                else:
                    # Find similar folders
                    similar = await self._find_similar_folders(
                        str(full_path.parent.relative_to(self.vault_path))
                    )
                    return PathValidationError(
                        message=f"Folder does not exist: {full_path.parent.relative_to(self.vault_path)}",
                        similar_folders=similar,
                    )

            # Check if note exists
            if full_path.exists() and not overwrite:
                return None

            async with aiofiles.open(full_path, "w", encoding="utf-8") as f:
                await f.write(content)

            folder, name = self._get_relative_path(full_path)
            logger.info(f"Created note: {full_path.relative_to(self.vault_path)}")

            return Note(
                path=str(full_path.relative_to(self.vault_path)),
                name=name,
                folder=folder,
                content=content,
            )

        except Exception as e:
            logger.error(f"Error creating note: {e}")
            return None

    async def update_note(self, path: str, content: str) -> Note | PathValidationError | None:
        """Update an existing note.

        Args:
            path: Relative path to the note
            content: New content

        Returns:
            Updated Note, PathValidationError if not found, or None on failure
        """
        try:
            full_path = self._resolve_path(path)

            if not full_path.exists():
                # Find similar notes
                similar = await self._find_similar_notes(path)
                return PathValidationError(
                    message=f"Note does not exist: {path}",
                    similar_folders=similar,
                )

            async with aiofiles.open(full_path, "w", encoding="utf-8") as f:
                await f.write(content)

            folder, name = self._get_relative_path(full_path)
            logger.info(f"Updated note: {full_path.relative_to(self.vault_path)}")

            return Note(
                path=str(full_path.relative_to(self.vault_path)),
                name=name,
                folder=folder,
                content=content,
            )

        except Exception as e:
            logger.error(f"Error updating note: {e}")
            return None

    async def append_to_note(self, path: str, content: str) -> Note | None:
        """Append content to an existing note.

        Args:
            path: Relative path to the note
            content: Content to append

        Returns:
            Updated Note or None if not found
        """
        try:
            full_path = self._resolve_path(path)

            if not full_path.exists():
                return None

            async with aiofiles.open(full_path, "a", encoding="utf-8") as f:
                await f.write("\n" + content)

            # Read full content
            async with aiofiles.open(full_path, "r", encoding="utf-8") as f:
                full_content = await f.read()

            folder, name = self._get_relative_path(full_path)
            logger.info(f"Appended to note: {full_path.relative_to(self.vault_path)}")

            return Note(
                path=str(full_path.relative_to(self.vault_path)),
                name=name,
                folder=folder,
                content=full_content,
            )

        except Exception as e:
            logger.error(f"Error appending to note: {e}")
            return None

    async def delete_note(self, path: str) -> bool:
        """Delete a note.

        Args:
            path: Relative path to the note

        Returns:
            True if deleted, False if not found
        """
        try:
            full_path = self._resolve_path(path)

            if not full_path.exists():
                return False

            await aiofiles.os.remove(full_path)
            logger.info(f"Deleted note: {full_path.relative_to(self.vault_path)}")
            return True

        except Exception as e:
            logger.error(f"Error deleting note: {e}")
            return False

    async def search_notes(
        self,
        query: str,
        folder: str | None = None,
        max_results: int = 20,
    ) -> list[SearchResult]:
        """Search notes by content.

        Args:
            query: Search query
            folder: Optional folder to search in
            max_results: Maximum number of results

        Returns:
            List of SearchResult objects
        """
        results = []
        search_path = self.vault_path / folder if folder else self.vault_path

        if not search_path.exists():
            return []

        try:
            pattern = re.compile(re.escape(query), re.IGNORECASE)

            for md_file in search_path.rglob("*.md"):
                if len(results) >= max_results:
                    break

                try:
                    async with aiofiles.open(md_file, "r", encoding="utf-8") as f:
                        content = await f.read()

                    matches = []
                    for i, line in enumerate(content.split("\n"), 1):
                        if pattern.search(line):
                            matches.append({
                                "line_num": i,
                                "line": line[:200],  # Truncate long lines
                            })

                    if matches:
                        folder_path, name = self._get_relative_path(md_file)
                        results.append(SearchResult(
                            path=str(md_file.relative_to(self.vault_path)),
                            name=name,
                            folder=folder_path,
                            matches=matches[:5],  # Max 5 matches per file
                        ))

                except Exception:
                    continue

        except Exception as e:
            logger.error(f"Error searching notes: {e}")

        return results

    async def move_note(self, old_path: str, new_path: str) -> Note | None:
        """Move or rename a note.

        Args:
            old_path: Current path
            new_path: New path

        Returns:
            Note at new location or None on failure
        """
        try:
            old_full = self._resolve_path(old_path)
            new_full = self._resolve_path(new_path)

            if not old_full.exists():
                return None

            if new_full.exists():
                return None

            # Create parent directory if needed
            await aiofiles.os.makedirs(new_full.parent, exist_ok=True)

            # Read content
            async with aiofiles.open(old_full, "r", encoding="utf-8") as f:
                content = await f.read()

            # Write to new location
            async with aiofiles.open(new_full, "w", encoding="utf-8") as f:
                await f.write(content)

            # Delete old file
            await aiofiles.os.remove(old_full)

            folder, name = self._get_relative_path(new_full)
            logger.info(f"Moved note: {old_path} -> {new_path}")

            return Note(
                path=str(new_full.relative_to(self.vault_path)),
                name=name,
                folder=folder,
                content=content,
            )

        except Exception as e:
            logger.error(f"Error moving note: {e}")
            return None

    async def list_folders(self) -> list[str]:
        """List all folders in the vault.

        Returns:
            List of folder paths relative to vault root
        """
        folders = []
        try:
            for item in self.vault_path.rglob("*"):
                if item.is_dir() and not item.name.startswith("."):
                    rel_path = str(item.relative_to(self.vault_path))
                    folders.append(rel_path)
        except Exception as e:
            logger.error(f"Error listing folders: {e}")

        return sorted(folders)

    async def list_notes(self, folder: str | None = None) -> list[dict[str, str]]:
        """List notes in the vault.

        Args:
            folder: Optional folder to list

        Returns:
            List of note info dicts
        """
        notes = []
        search_path = self.vault_path / folder if folder else self.vault_path

        if not search_path.exists():
            return []

        try:
            for md_file in search_path.rglob("*.md"):
                if md_file.name.startswith("."):
                    continue

                folder_path, name = self._get_relative_path(md_file)
                notes.append({
                    "path": str(md_file.relative_to(self.vault_path)),
                    "name": name,
                    "folder": folder_path,
                })
        except Exception as e:
            logger.error(f"Error listing notes: {e}")

        return sorted(notes, key=lambda n: (n["folder"], n["name"]))

    async def get_tags(self, path: str) -> list[str]:
        """Get tags from a note.

        Args:
            path: Path to the note

        Returns:
            List of tags found
        """
        note = await self.read_note(path)
        if not note:
            return []

        # Find tags: #tag or tags in frontmatter
        tags = set()

        # Inline tags
        for match in re.finditer(r"#([a-zA-Z0-9_-]+)", note.content):
            tags.add(match.group(1))

        # Frontmatter tags
        if note.content.startswith("---"):
            parts = note.content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                for line in frontmatter.split("\n"):
                    if line.strip().startswith("tags:"):
                        # YAML list format
                        tag_part = line.split(":", 1)[1].strip()
                        if tag_part.startswith("["):
                            # Inline list
                            for tag in re.findall(r"[a-zA-Z0-9_-]+", tag_part):
                                tags.add(tag)
                        else:
                            tags.add(tag_part)
                    elif line.strip().startswith("- "):
                        tags.add(line.strip()[2:])

        return sorted(tags)

    async def search_by_tag(
        self,
        tag: str,
        folder: str | None = None,
    ) -> list[dict[str, str]]:
        """Find notes with a specific tag.

        Args:
            tag: Tag to search for (without #)
            folder: Optional folder to search in

        Returns:
            List of note info dicts
        """
        results = []
        notes = await self.list_notes(folder)

        for note_info in notes:
            tags = await self.get_tags(note_info["path"])
            if tag.lower() in [t.lower() for t in tags]:
                results.append(note_info)

        return results

    async def get_backlinks(self, path: str) -> list[dict[str, Any]]:
        """Find notes that link to the specified note.

        Args:
            path: Path to the target note

        Returns:
            List of linking notes with link text
        """
        results = []
        target_name = Path(path).stem

        # Pattern for wiki-style links: [[note]] or [[note|alias]]
        pattern = re.compile(
            rf"\[\[{re.escape(target_name)}(\|[^\]]+)?\]\]",
            re.IGNORECASE,
        )

        notes = await self.list_notes()
        for note_info in notes:
            if note_info["path"] == path:
                continue

            note = await self.read_note(note_info["path"])
            if not note:
                continue

            matches = pattern.findall(note.content)
            if matches:
                results.append({
                    "path": note_info["path"],
                    "name": note_info["name"],
                    "folder": note_info["folder"],
                    "link_text": f"[[{target_name}]]",
                })

        return results

    async def _find_similar_folders(self, target: str) -> list[str]:
        """Find folders similar to the target path."""
        folders = await self.list_folders()
        target_lower = target.lower()

        # Simple similarity: common prefix or substring match
        similar = []
        for folder in folders:
            folder_lower = folder.lower()
            if target_lower in folder_lower or folder_lower in target_lower:
                similar.append(folder)

        return similar[:5]

    async def _find_similar_notes(self, target: str) -> list[str]:
        """Find notes similar to the target path."""
        notes = await self.list_notes()
        target_lower = Path(target).stem.lower()

        similar = []
        for note in notes:
            name_lower = Path(note["name"]).stem.lower()
            if target_lower in name_lower or name_lower in target_lower:
                similar.append(note["path"])

        return similar[:5]
