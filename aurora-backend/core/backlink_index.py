import re
from dataclasses import dataclass
from typing import List, Dict, Set

from data.models import Note
from core.link_resolver import LinkResolver

@dataclass
class Backlink:
    source_path: str
    target_path: str
    context_snippet: str
    link_text: str


class BacklinkIndex:
    """
    Reverse link index for an Obsidian vault.
    Builds an index of notes that link to other notes, including surrounding context.
    """
    def __init__(self):
        self.index: Dict[str, List[Backlink]] = {}
        self.outlinks: Dict[str, int] = {}
        self.all_notes: Set[str] = set()

    def rebuild_index(self, notes_cache: Dict[str, Note]) -> None:
        """
        Rebuilds the backlink index from the provided notes cache.
        """
        self.index = {path: [] for path in notes_cache}
        self.outlinks = {path: 0 for path in notes_cache}
        self.all_notes = set(notes_cache.keys())
        
        resolver = LinkResolver(notes_cache)
        
        # Regex to find wiki links
        link_pattern = re.compile(r"(\[\[([^\]]+)\]\])")
        
        for path, note in notes_cache.items():
            content = note.content
            outlink_count = 0
            
            for match in link_pattern.finditer(content):
                full_link = match.group(1)
                
                parsed_link = resolver.parse_link(full_link)
                
                if parsed_link.resolved and parsed_link.target_note:
                    outlink_count += 1
                    
                    # Extract surrounding context (±50 chars)
                    start = max(0, match.start() - 50)
                    end = min(len(content), match.end() + 50)
                    context = content[start:end].replace("\n", " ")
                    
                    backlink = Backlink(
                        source_path=path,
                        target_path=parsed_link.target_note,
                        context_snippet=context,
                        link_text=full_link
                    )
                    
                    if parsed_link.target_note in self.index:
                        self.index[parsed_link.target_note].append(backlink)
                        
            self.outlinks[path] = outlink_count

    def get_backlinks(self, note_path: str) -> List[Backlink]:
        """
        Returns a list of backlinks for the given note path.
        """
        return self.index.get(note_path, [])

    def get_orphan_notes(self) -> List[str]:
        """
        Returns a list of note paths that have no inlinks and no outlinks.
        """
        orphans = []
        for path in self.all_notes:
            inlinks = len(self.index.get(path, []))
            outlinks = self.outlinks.get(path, 0)
            if inlinks == 0 and outlinks == 0:
                orphans.append(path)
        return orphans
