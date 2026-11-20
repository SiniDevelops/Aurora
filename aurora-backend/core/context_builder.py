"""
Context Builder — assembles vault context for LLM prompts.

Pipeline:
1. Section-level retrieval: keyword search over heading-based chunks, merged
   with ChromaDB semantic hits when a real embedding provider is configured.
2. Group hits by note; each primary note carries only its relevant sections.
3. Graph expansion: 1-hop neighbours of the top notes (via the knowledge
   graph) are added as short "linked note" excerpts, ranked by how many of the
   primary notes they connect to.
4. Everything is trimmed to the token budget, primary notes first.
"""

from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from .vault_manager import VaultManager
from .chunker import estimate_tokens
from data.models import Note, ChatSession

MAX_PRIMARY_NOTES = 5
MAX_SECTIONS_PER_NOTE = 3
MAX_LINKED_NOTES = 3
GRAPH_SEED_NOTES = 3
LINKED_EXCERPT_CHARS = 600
LINKED_BUDGET_SHARE = 0.25  # at most 25% of the budget goes to linked notes


class VaultContext(BaseModel):
    notes: List[Note]                                   # primary notes (content = relevant sections)
    recent_notes: List[Note]
    tags: dict
    tree: dict
    linked_notes: List[Note] = Field(default_factory=list)  # graph neighbours (content = excerpt)
    linked_via: Dict[str, List[str]] = Field(default_factory=dict)  # linked path -> primary titles


class ContextBuilder:
    """Builds context for LLM prompts from the vault."""

    def __init__(self, vault_manager: VaultManager, chroma_store: Any, embedding_manager: Any,
                 indexer: Any = None, graph_getter: Optional[Callable[[], Any]] = None):
        self.vault_manager = vault_manager
        self.chroma_store = chroma_store
        self.embedding_manager = embedding_manager
        self.indexer = indexer
        # The graph object is replaced on every vault change, so look it up lazily
        self.graph_getter = graph_getter

    async def build_context(self, query: str, session: Optional[ChatSession] = None,
                            active_note: Optional[Note] = None, max_tokens: int = 4000) -> VaultContext:
        """Build vault context within token budget."""
        primary = await self._retrieve_primary(query)

        if active_note and all(n.path != active_note.path for n in primary):
            primary.insert(0, active_note)

        linked, linked_via = self._expand_with_graph(primary)

        linked_budget = int(max_tokens * LINKED_BUDGET_SHARE) if linked else 0
        primary = self._trim_to_budget(primary, max_tokens - linked_budget)
        used = sum(estimate_tokens(n.content) for n in primary)
        linked = self._trim_to_budget(linked, max_tokens - used)
        linked_via = {n.path: linked_via[n.path] for n in linked}

        recent = await self.vault_manager.get_recent_notes(limit=5)
        tags = await self.vault_manager.get_all_tags()
        tree = await self.vault_manager.get_vault_tree()

        return VaultContext(
            notes=primary,
            recent_notes=recent,
            tags=tags,
            tree=tree,
            linked_notes=linked,
            linked_via=linked_via,
        )

    # ─── Retrieval ───────────────────────────────────

    async def _retrieve_primary(self, query: str) -> List[Note]:
        cache = self.vault_manager.notes_cache

        if self.indexer is None:
            # Fallback: whole-note substring search
            return await self.vault_manager.search_notes(query, limit=MAX_PRIMARY_NOTES)

        hits = self.indexer.search_chunks(query, limit=20)
        semantic = await self.indexer.semantic_search(query, limit=10)

        # Merge: normalise each list to 0..1 so neither dominates
        scored: Dict[tuple, float] = {}
        chunk_by_key: Dict[tuple, Any] = {}
        for hit_list in (hits, semantic):
            if not hit_list:
                continue
            top = max(h.score for h in hit_list) or 1.0
            for h in hit_list:
                key = (h.path, h.chunk.chunk_index)
                scored[key] = scored.get(key, 0.0) + h.score / top
                chunk_by_key[key] = h.chunk

        # Group sections by note, rank notes by their best section
        by_note: Dict[str, List[tuple]] = {}
        for key, score in scored.items():
            by_note.setdefault(key[0], []).append((score, chunk_by_key[key]))

        ranked = sorted(by_note.items(), key=lambda kv: max(s for s, _ in kv[1]), reverse=True)

        primary: List[Note] = []
        for path, sections in ranked[:MAX_PRIMARY_NOTES]:
            note = cache.get(path)
            if note is None:
                continue
            best = sorted(sections, key=lambda s: s[0], reverse=True)[:MAX_SECTIONS_PER_NOTE]
            best.sort(key=lambda s: s[1].chunk_index)  # keep document order
            body = "\n\n".join(c.content for _, c in best)
            primary.append(note.model_copy(update={"content": body}))
        return primary

    def _expand_with_graph(self, primary: List[Note]):
        graph = self.graph_getter() if self.graph_getter else None
        if graph is None or not primary:
            return [], {}

        cache = self.vault_manager.notes_cache
        primary_paths = {n.path for n in primary}
        via: Dict[str, List[str]] = {}

        for note in primary[:GRAPH_SEED_NOTES]:
            for neighbor in graph.get_neighbors(note.path, depth=1):
                if neighbor in primary_paths or neighbor not in cache:
                    continue
                via.setdefault(neighbor, []).append(note.title)

        # Prefer neighbours shared by several primary notes, then well-connected ones
        def rank(path: str):
            connections = graph.nodes.get(path, {}).get("connections", 0)
            return (len(via[path]), connections)

        linked: List[Note] = []
        for path in sorted(via, key=rank, reverse=True)[:MAX_LINKED_NOTES]:
            note = cache[path]
            excerpt = (note.clean_content or "")[:LINKED_EXCERPT_CHARS].strip()
            if len(note.clean_content or "") > LINKED_EXCERPT_CHARS:
                excerpt += " …"
            linked.append(note.model_copy(update={"content": excerpt}))
        return linked, via

    # ─── Budget ──────────────────────────────────────

    def _estimate_tokens(self, text: str) -> int:
        """Rough estimate (~4 chars per token)."""
        return estimate_tokens(text)

    def _trim_to_budget(self, notes: List[Note], budget: int) -> List[Note]:
        """Keep notes in order until the budget runs out."""
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
