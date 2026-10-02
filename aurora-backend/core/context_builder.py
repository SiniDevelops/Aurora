from typing import List, Optional, Any
from pydantic import BaseModel
from .vault_manager import VaultManager
from data.models import Note, ChatSession

class VaultContext(BaseModel):
    notes: List[Note]
    recent_notes: List[Note]
    tags: dict
    tree: dict

class ContextBuilder:
    """Builds context for LLM prompts from the vault."""
    
    def __init__(self, vault_manager: VaultManager, chroma_store: Any, embedding_manager: Any):
        self.vault_manager = vault_manager
        self.chroma_store = chroma_store
        self.embedding_manager = embedding_manager
        
    async def build_context(self, query: str, session: Optional[ChatSession] = None, active_note: Optional[Note] = None, max_tokens: int = 4000) -> VaultContext:
        """Build vault context within token budget."""
        notes = await self.vault_manager.search_notes(query, limit=5)
        
        if active_note and active_note not in notes:
            notes.insert(0, active_note)
            
        recent = await self.vault_manager.get_recent_notes(limit=5)
        tags = await self.vault_manager.get_all_tags()
        tree = await self.vault_manager.get_vault_tree()
        
        trimmed_notes = self._trim_to_budget(notes, max_tokens)
        
        return VaultContext(
            notes=trimmed_notes,
            recent_notes=recent,
            tags=tags,
            tree=tree
        )
        
    def _estimate_tokens(self, text: str) -> int:
        """Rough estimate (~4 chars per token)."""
        return len(text) // 4
        
    def _trim_to_budget(self, notes: List[Note], budget: int) -> List[Note]:
        """Trim notes to fit within budget."""
        trimmed = []
        current_tokens = 0
        for note in notes:
            est = self._estimate_tokens(note.content)
            if current_tokens + est <= budget:
                trimmed.append(note)
                current_tokens += est
            else:
                break
        return trimmed
