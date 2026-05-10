"""Tests for ObsidianService - file operations for Obsidian vault."""

from __future__ import annotations

from pathlib import Path

import pytest

from obsidian_agent.service import (
    Note,
    ObsidianService,
    PathValidationError,
    SearchResult,
)


class TestServiceInit:
    """Tests for ObsidianService initialization."""

    def test_init_with_valid_path(self, temp_vault: Path) -> None:
        """Service initializes with valid vault path."""
        service = ObsidianService(str(temp_vault))
        assert service.vault_path == temp_vault.resolve()

    def test_init_with_invalid_path(self) -> None:
        """Service raises error for non-existent path."""
        with pytest.raises(ValueError, match="does not exist"):
            ObsidianService("/nonexistent/path")


class TestPathResolution:
    """Tests for path resolution and security."""

    def test_resolve_path_adds_md_extension(self, service: ObsidianService) -> None:
        """Path resolution adds .md extension if missing."""
        path = service._resolve_path("note")
        assert path.suffix == ".md"

    def test_resolve_path_preserves_md_extension(self, service: ObsidianService) -> None:
        """Path resolution preserves existing .md extension."""
        path = service._resolve_path("note.md")
        assert path.name == "note.md"

    def test_resolve_path_strips_leading_slash(self, service: ObsidianService) -> None:
        """Path resolution strips leading slash."""
        path = service._resolve_path("/note.md")
        assert not str(path.relative_to(service.vault_path)).startswith("/")

    def test_resolve_path_prevents_escape(self, service: ObsidianService) -> None:
        """Path resolution prevents escaping vault with ../."""
        with pytest.raises(ValueError, match="escapes vault"):
            service._resolve_path("../../../etc/passwd")

    def test_resolve_path_nested(self, service: ObsidianService) -> None:
        """Path resolution handles nested paths."""
        path = service._resolve_path("Projects/Work/note")
        assert "Projects" in str(path)
        assert "Work" in str(path)


class TestReadNote:
    """Tests for reading notes."""

    @pytest.mark.asyncio
    async def test_read_existing_note(self, service: ObsidianService) -> None:
        """Reading existing note returns Note object."""
        note = await service.read_note("README")
        assert note is not None
        assert isinstance(note, Note)
        assert "My Vault" in note.content
        assert note.name == "README.md"

    @pytest.mark.asyncio
    async def test_read_nested_note(self, service: ObsidianService) -> None:
        """Reading nested note works correctly."""
        note = await service.read_note("Projects/duq")
        assert note is not None
        assert "DUQ Project" in note.content
        assert note.folder == "Projects"

    @pytest.mark.asyncio
    async def test_read_nonexistent_note(self, service: ObsidianService) -> None:
        """Reading non-existent note returns None."""
        note = await service.read_note("nonexistent")
        assert note is None


class TestCreateNote:
    """Tests for creating notes."""

    @pytest.mark.asyncio
    async def test_create_note_in_root(self, service: ObsidianService) -> None:
        """Creating note in vault root works."""
        result = await service.create_note("new_note", "Content here")
        assert isinstance(result, Note)
        assert result.name == "new_note.md"
        assert result.content == "Content here"

    @pytest.mark.asyncio
    async def test_create_note_in_existing_folder(self, service: ObsidianService) -> None:
        """Creating note in existing folder works."""
        result = await service.create_note("Daily/new_daily", "Daily content")
        assert isinstance(result, Note)
        assert result.folder == "Daily"

    @pytest.mark.asyncio
    async def test_create_note_fails_without_overwrite(self, service: ObsidianService) -> None:
        """Creating note over existing fails without overwrite flag."""
        result = await service.create_note("README", "New content")
        assert result is None

    @pytest.mark.asyncio
    async def test_create_note_with_overwrite(self, service: ObsidianService) -> None:
        """Creating note with overwrite replaces existing."""
        result = await service.create_note("README", "Replaced content", overwrite=True)
        assert isinstance(result, Note)
        assert result.content == "Replaced content"

    @pytest.mark.asyncio
    async def test_create_note_missing_folder_returns_error(
        self, service: ObsidianService
    ) -> None:
        """Creating note in non-existent folder returns PathValidationError."""
        result = await service.create_note("NewFolder/note", "Content")
        assert isinstance(result, PathValidationError)
        assert "does not exist" in result.message

    @pytest.mark.asyncio
    async def test_create_note_with_create_folders(self, service: ObsidianService) -> None:
        """Creating note with create_folders creates missing directories."""
        result = await service.create_note(
            "NewFolder/SubFolder/note", "Content", create_folders=True
        )
        assert isinstance(result, Note)
        assert "NewFolder" in result.folder


class TestUpdateNote:
    """Tests for updating notes."""

    @pytest.mark.asyncio
    async def test_update_existing_note(self, service: ObsidianService) -> None:
        """Updating existing note replaces content."""
        result = await service.update_note("README", "Updated content")
        assert isinstance(result, Note)
        assert result.content == "Updated content"

    @pytest.mark.asyncio
    async def test_update_nonexistent_note(self, service: ObsidianService) -> None:
        """Updating non-existent note returns PathValidationError."""
        result = await service.update_note("nonexistent", "Content")
        assert isinstance(result, PathValidationError)


class TestAppendNote:
    """Tests for appending to notes."""

    @pytest.mark.asyncio
    async def test_append_to_existing_note(self, service: ObsidianService) -> None:
        """Appending to existing note adds content."""
        result = await service.append_to_note("README", "Appended text")
        assert isinstance(result, Note)
        assert "My Vault" in result.content
        assert "Appended text" in result.content

    @pytest.mark.asyncio
    async def test_append_to_nonexistent_note(self, service: ObsidianService) -> None:
        """Appending to non-existent note returns None."""
        result = await service.append_to_note("nonexistent", "Content")
        assert result is None


class TestDeleteNote:
    """Tests for deleting notes."""

    @pytest.mark.asyncio
    async def test_delete_existing_note(self, service: ObsidianService, temp_vault: Path) -> None:
        """Deleting existing note removes file."""
        assert (temp_vault / "README.md").exists()
        result = await service.delete_note("README")
        assert result is True
        assert not (temp_vault / "README.md").exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_note(self, service: ObsidianService) -> None:
        """Deleting non-existent note returns False."""
        result = await service.delete_note("nonexistent")
        assert result is False


class TestSearchNotes:
    """Tests for searching notes."""

    @pytest.mark.asyncio
    async def test_search_finds_matches(self, service: ObsidianService) -> None:
        """Search finds notes with matching content."""
        results = await service.search_notes("DUQ")
        assert len(results) > 0
        assert any(isinstance(r, SearchResult) for r in results)

    @pytest.mark.asyncio
    async def test_search_in_folder(self, service: ObsidianService) -> None:
        """Search in specific folder limits scope."""
        results = await service.search_notes("project", folder="Projects")
        assert all("Projects" in r.folder or r.folder == "" for r in results)

    @pytest.mark.asyncio
    async def test_search_respects_max_results(self, service: ObsidianService) -> None:
        """Search respects max_results limit."""
        results = await service.search_notes("md", max_results=1)
        assert len(results) <= 1

    @pytest.mark.asyncio
    async def test_search_no_matches(self, service: ObsidianService) -> None:
        """Search with no matches returns empty list."""
        results = await service.search_notes("xyz123nonexistent")
        assert len(results) == 0


class TestMoveNote:
    """Tests for moving/renaming notes."""

    @pytest.mark.asyncio
    async def test_move_note_to_new_location(self, service: ObsidianService) -> None:
        """Moving note to new location works."""
        result = await service.move_note("README", "Archive/README")
        assert isinstance(result, Note)
        assert result.folder == "Archive"

    @pytest.mark.asyncio
    async def test_rename_note(self, service: ObsidianService) -> None:
        """Renaming note in same folder works."""
        result = await service.move_note("README", "README_renamed")
        assert isinstance(result, Note)
        assert result.name == "README_renamed.md"

    @pytest.mark.asyncio
    async def test_move_nonexistent_note(self, service: ObsidianService) -> None:
        """Moving non-existent note returns None."""
        result = await service.move_note("nonexistent", "new_location")
        assert result is None

    @pytest.mark.asyncio
    async def test_move_to_existing_target(self, service: ObsidianService) -> None:
        """Moving to existing target returns None."""
        result = await service.move_note("README", "Daily/2026-05-10")
        assert result is None


class TestListOperations:
    """Tests for listing folders and notes."""

    @pytest.mark.asyncio
    async def test_list_folders(self, service: ObsidianService) -> None:
        """List folders returns all directories."""
        folders = await service.list_folders()
        assert "Daily" in folders
        assert "Projects" in folders
        assert "Archive" in folders

    @pytest.mark.asyncio
    async def test_list_folders_includes_nested(self, service: ObsidianService) -> None:
        """List folders includes nested directories."""
        folders = await service.list_folders()
        assert any("Work" in f for f in folders)

    @pytest.mark.asyncio
    async def test_list_notes_all(self, service: ObsidianService) -> None:
        """List all notes in vault."""
        notes = await service.list_notes()
        assert len(notes) >= 4  # README + daily + duq + meeting
        assert all("path" in n and "name" in n for n in notes)

    @pytest.mark.asyncio
    async def test_list_notes_in_folder(self, service: ObsidianService) -> None:
        """List notes in specific folder."""
        notes = await service.list_notes("Daily")
        assert len(notes) == 1
        assert notes[0]["name"] == "2026-05-10.md"


class TestTags:
    """Tests for tag operations."""

    @pytest.mark.asyncio
    async def test_get_tags_inline(self, service: ObsidianService) -> None:
        """Get inline tags from note."""
        tags = await service.get_tags("Daily/2026-05-10")
        assert "daily" in tags
        assert "log" in tags

    @pytest.mark.asyncio
    async def test_get_tags_nonexistent(self, service: ObsidianService) -> None:
        """Get tags from non-existent note returns empty list."""
        tags = await service.get_tags("nonexistent")
        assert tags == []

    @pytest.mark.asyncio
    async def test_search_by_tag(self, service: ObsidianService) -> None:
        """Search by tag finds matching notes."""
        results = await service.search_by_tag("project")
        assert len(results) >= 1
        assert any("duq" in r["name"].lower() for r in results)

    @pytest.mark.asyncio
    async def test_search_by_tag_in_folder(self, service: ObsidianService) -> None:
        """Search by tag in specific folder."""
        results = await service.search_by_tag("work", folder="Projects/Work")
        assert len(results) == 1


class TestBacklinks:
    """Tests for backlink operations."""

    @pytest.mark.asyncio
    async def test_get_backlinks(self, service: ObsidianService) -> None:
        """Get backlinks finds linking notes."""
        results = await service.get_backlinks("README")
        # Projects/duq.md links to [[README]]
        assert len(results) >= 1
        assert any("duq" in r["name"].lower() for r in results)

    @pytest.mark.asyncio
    async def test_get_backlinks_no_links(self, service: ObsidianService) -> None:
        """Get backlinks for note with no incoming links."""
        results = await service.get_backlinks("Daily/2026-05-10")
        # No other notes link to the daily note
        assert len(results) == 0


class TestSimilarPaths:
    """Tests for similar path suggestions."""

    @pytest.mark.asyncio
    async def test_find_similar_folders(self, service: ObsidianService) -> None:
        """Find similar folders suggests related paths."""
        similar = await service._find_similar_folders("Proj")
        assert any("Projects" in f for f in similar)

    @pytest.mark.asyncio
    async def test_find_similar_notes(self, service: ObsidianService) -> None:
        """Find similar notes suggests related notes."""
        similar = await service._find_similar_notes("readme")
        assert any("README" in n for n in similar)
