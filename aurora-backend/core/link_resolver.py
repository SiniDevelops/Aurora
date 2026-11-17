import re
from dataclasses import dataclass
from typing import Optional, Dict

from data.models import Note

@dataclass
class LinkTarget:
    target_note: Optional[str]
    display_text: str
    link_type: str
    resolved: bool
    heading: Optional[str] = None
    block_ref: Optional[str] = None


class LinkResolver:
    """
    Full Obsidian link resolution engine.
    Parses wiki links, aliases, headings, and block references.
    Resolves links against the vault's notes_cache.
    """
    def __init__(self, notes_cache: Dict[str, Note]):
        self.notes_cache = notes_cache
        
        # Build lookup maps for faster resolution
        self.title_map = {}
        self.filename_map = {}
        self.alias_map = {}
        
        for path, note in notes_cache.items():
            self.title_map[note.title.lower()] = path
            self.filename_map[note.filename.lower()] = path
            self.filename_map[note.filename.lower().replace(".md", "")] = path
            for alias in note.aliases:
                self.alias_map[alias.lower()] = path

    def parse_link(self, link_text: str) -> LinkTarget:
        """
        Parses an Obsidian wiki link and returns a LinkTarget object.
        Supports [[note]], [[note|alias]], [[note#heading]], [[note#^blockref]]
        """
        # Remove surrounding brackets if present
        if link_text.startswith("[[") and link_text.endswith("]]"):
            link_text = link_text[2:-2]
            
        target = link_text
        display_text = link_text
        heading = None
        block_ref = None
        
        # Handle alias
        if "|" in target:
            target, display_text = target.split("|", 1)
        
        link_type = "wiki"
        if display_text != target and display_text != link_text:
            link_type = "alias"
            
        # Handle block ref and heading
        if "#^" in target:
            target, block_ref = target.split("#^", 1)
            link_type = "block"
        elif "#" in target:
            target, heading = target.split("#", 1)
            link_type = "heading"
            
        target = target.strip()
        resolved_path = self.resolve_path(target)
        
        return LinkTarget(
            target_note=resolved_path,
            display_text=display_text.strip(),
            link_type=link_type,
            resolved=resolved_path is not None,
            heading=heading.strip() if heading else None,
            block_ref=block_ref.strip() if block_ref else None
        )

    def resolve_path(self, target: str) -> Optional[str]:
        """
        Resolves a target string to a note path using case-insensitive matching.
        Matches by title, filename, or alias.
        """
        if not target:
            return None
            
        target_lower = target.lower()
        
        # 1. Exact path match in cache
        for path in self.notes_cache:
            if path.lower() == target_lower:
                return path
        
        # 2. Match by title
        if target_lower in self.title_map:
            return self.title_map[target_lower]
        
        # 3. Match by filename
        if target_lower in self.filename_map:
            return self.filename_map[target_lower]
            
        # 4. Match by alias
        if target_lower in self.alias_map:
            return self.alias_map[target_lower]
            
        return None
