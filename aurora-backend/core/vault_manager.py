"""
Vault Manager — Reads, indexes, and manages the Obsidian vault on disk.

Provides:
- File discovery and indexing
- Note reading with frontmatter parsing
- Text search across cached notes
- Vault statistics and tag aggregation
"""

import os
import re
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from data.models import Note

logger = logging.getLogger("aurora.vault")

# Regex for YAML frontmatter between --- delimiters
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
# Regex for wiki links [[target|display]]
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
# Regex for tags #tag-name (not inside code blocks)
TAG_RE = re.compile(r"(?:^|\s)#([\w\-/]+)", re.MULTILINE)


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content.
    Returns (frontmatter_dict, content_without_frontmatter).
    """
    match = FRONTMATTER_RE.match(content)
    if not match:
        return {}, content

    raw_fm = match.group(1)
    body = content[match.end():]
    fm: dict = {}

    for line in raw_fm.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            # Handle list values like [a, b, c]
            if val.startswith("[") and val.endswith("]"):
                items = [i.strip().strip("'\"") for i in val[1:-1].split(",") if i.strip()]
                fm[key] = items
            elif val.lower() in ("true", "false"):
                fm[key] = val.lower() == "true"
            elif val.startswith('"') and val.endswith('"'):
                fm[key] = val[1:-1]
            else:
                fm[key] = val

    return fm, body


def _extract_tags(content: str, frontmatter: dict) -> list[str]:
    """Extract tags from frontmatter and inline #tags."""
    tags = set()
    # From frontmatter
    fm_tags = frontmatter.get("tags", [])
    if isinstance(fm_tags, list):
        tags.update(fm_tags)
    elif isinstance(fm_tags, str):
        tags.update(t.strip() for t in fm_tags.split(","))

    # Inline #tags
    for match in TAG_RE.finditer(content):
        tags.add(match.group(1))

    return sorted(tags)


def _extract_links(content: str) -> list[dict]:
    """Extract [[wiki links]] from content."""
    links = []
    for match in WIKILINK_RE.finditer(content):
        target = match.group(1).strip()
        display = match.group(2)
        links.append({
            "target": target,
            "display_text": display.strip() if display else None,
            "link_type": "wiki",
        })
    return links


class VaultManager:
    """Manages interactions with the local Obsidian vault."""

    def __init__(self, vault_path: str, excluded_folders: List[str], supported_extensions: List[str]):
        self.vault_path = vault_path
        self.excluded_folders = excluded_folders
        self.supported_extensions = supported_extensions
        self.notes_cache: Dict[str, Note] = {}

    async def initialize(self) -> None:
        """Walk vault, build initial index."""
        files = await self.discover_files()
        indexed = 0
        for f in files:
            try:
                await self.read_note(f)
                indexed += 1
            except Exception as e:
                logger.warning(f"Failed to index {f}: {e}")
        logger.info(f"Vault indexed: {indexed}/{len(files)} notes")

    async def discover_files(self) -> List[str]:
        """Walk directory, filter by extension, exclude folders."""
        valid_files = []
        for root, dirs, files in os.walk(self.vault_path):
            dirs[:] = [d for d in dirs if d not in self.excluded_folders and not d.startswith(".")]
            for file in files:
                if any(file.endswith(ext) for ext in self.supported_extensions):
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, self.vault_path).replace("\\", "/")
                    valid_files.append(rel_path)
        return valid_files

    async def read_note(self, path: str) -> Note:
        """Read a file and parse it into a Note model."""
        abs_path = os.path.join(self.vault_path, path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Note not found: {path}")

        with open(abs_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        frontmatter, clean_content = _parse_frontmatter(raw_content)
        tags = _extract_tags(raw_content, frontmatter)
        links = _extract_links(raw_content)

        filename = os.path.basename(path)
        folder = os.path.dirname(path) or "/"
        title = frontmatter.get("title", filename.replace(".md", ""))
        stat = os.stat(abs_path)

        note = Note(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, path)),
            path=path,
            filename=filename,
            folder=folder,
            title=title,
            content=raw_content,
            clean_content=clean_content.strip(),
            frontmatter=frontmatter,
            tags=tags,
            aliases=frontmatter.get("aliases", []) if isinstance(frontmatter.get("aliases"), list) else [],
            links=links,
            created_at=datetime.fromtimestamp(stat.st_ctime),
            modified_at=datetime.fromtimestamp(stat.st_mtime),
            word_count=len(clean_content.split()),
        )

        self.notes_cache[path] = note
        return note

    async def write_note(self, path: str, content: str, frontmatter: Optional[Dict[str, Any]] = None) -> Note:
        """Write a note to the vault."""
        # Sanitize path: strip leading slashes, prevent directory traversal
        path = path.lstrip("/").lstrip("\\")
        if not path:
            path = "Inbox/Untitled.md"
        if not path.endswith(".md"):
            path += ".md"
        
        abs_path = os.path.join(self.vault_path, path)
        # Safety: ensure we're still inside the vault
        abs_path = os.path.abspath(abs_path)
        if not abs_path.startswith(os.path.abspath(self.vault_path)):
            raise ValueError(f"Path escapes vault: {path}")
        
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        with open(abs_path, "w", encoding="utf-8") as f:
            if frontmatter:
                f.write("---\n")
                for k, v in frontmatter.items():
                    if isinstance(v, list):
                        f.write(f"{k}: [{', '.join(str(i) for i in v)}]\n")
                    else:
                        f.write(f"{k}: {v}\n")
                f.write("---\n\n")
            f.write(content)

        return await self.read_note(path)

    async def delete_note(self, path: str) -> bool:
        """Delete a note from the vault."""
        abs_path = os.path.join(self.vault_path, path)
        if os.path.exists(abs_path):
            os.remove(abs_path)
            self.notes_cache.pop(path, None)
            return True
        return False

    async def get_vault_tree(self) -> Dict[str, Any]:
        """Return nested dict representing folder structure."""
        tree: Dict[str, Any] = {}
        for path in self.notes_cache.keys():
            parts = path.split("/")
            curr = tree
            for part in parts[:-1]:
                if part not in curr:
                    curr[part] = {}
                curr = curr[part]
            curr[parts[-1]] = "file"
        return tree

    async def get_recent_notes(self, limit: int = 10) -> List[Note]:
        """Get most recently modified notes."""
        sorted_notes = sorted(
            self.notes_cache.values(),
            key=lambda n: n.modified_at,
            reverse=True,
        )
        return sorted_notes[:limit]

    async def search_notes(self, query: str, limit: int = 10) -> List[Note]:
        """Text search across cached notes (title, content, tags)."""
        results = []
        query_lower = query.lower()
        for note in self.notes_cache.values():
            score = 0
            if query_lower in note.title.lower():
                score += 3
            if any(query_lower in tag.lower() for tag in note.tags):
                score += 2
            if query_lower in note.clean_content.lower():
                score += 1
            if score > 0:
                results.append((score, note))

        results.sort(key=lambda x: x[0], reverse=True)
        return [note for _, note in results[:limit]]

    async def get_vault_stats(self) -> Dict[str, Any]:
        """Get vault statistics."""
        total_notes = len(self.notes_cache)
        total_words = sum(n.word_count for n in self.notes_cache.values())
        all_tags = await self.get_all_tags()
        return {
            "total_notes": total_notes,
            "total_words": total_words,
            "total_tags": len(all_tags),
            "total_links": sum(len(n.links) for n in self.notes_cache.values()),
        }

    async def get_all_tags(self) -> Dict[str, int]:
        """Return tag cloud with counts."""
        tag_counts: Dict[str, int] = {}
        for note in self.notes_cache.values():
            for tag in note.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        return tag_counts

    async def refresh_note(self, path: str) -> Note:
        """Re-read and update cache for a single note."""
        return await self.read_note(path)
