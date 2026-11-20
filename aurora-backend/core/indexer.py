"""
Vault Indexer — incremental, hash-based indexing of note chunks.

Responsibilities:
- Chunk every note by headings (core.chunker) and keep an in-memory chunk index
  used for section-level keyword search.
- Detect real content changes via SHA-256 hashes so duplicate watcher events
  and no-op saves don't trigger re-indexing or graph rebuilds.
- Embed changed chunks into ChromaDB when a real embedding provider is
  configured. Which hashes have been embedded (and under which provider) is
  persisted to disk, so a restart only re-embeds notes that changed.
"""

import hashlib
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from data.models import Note, NoteChunk
from core.chunker import chunk_note

logger = logging.getLogger("aurora.indexer")

STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "any", "can", "had",
    "her", "was", "one", "our", "out", "has", "have", "him", "his", "how", "its",
    "may", "new", "now", "old", "see", "two", "who", "did", "get", "let", "say",
    "she", "too", "use", "what", "when", "where", "which", "why", "with", "this",
    "that", "from", "they", "will", "would", "there", "their", "about", "into",
    "your", "some", "than", "then", "them", "these", "those", "been", "were",
    "does", "just", "like", "also", "more", "most", "such", "only", "very",
    "tell", "show", "give", "find", "note", "notes", "write", "wrote", "please",
    "my", "me", "is", "it", "in", "on", "of", "to", "a", "an", "do", "i",
}
WORD_RE = re.compile(r"[a-z0-9][a-z0-9\-']+")


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def query_terms(query: str) -> List[str]:
    """Lowercase significant words from a query (stopwords removed, deduped)."""
    seen: List[str] = []
    for w in WORD_RE.findall(query.lower()):
        w = w.strip("'-")
        if len(w) >= 3 and w not in STOPWORDS and w not in seen:
            seen.append(w)
    return seen


@dataclass
class ChunkHit:
    path: str
    chunk: NoteChunk
    score: float


class VaultIndexer:
    def __init__(self, vault_manager, chroma_store=None, embedding_manager=None,
                 state_path: Optional[str] = None):
        self.vault_manager = vault_manager
        self.chroma_store = chroma_store
        self.embedding_manager = embedding_manager
        self.state_path = Path(state_path) if state_path else None

        self.chunks: Dict[str, List[NoteChunk]] = {}   # path -> chunks
        self._seen: Dict[str, str] = {}                 # path -> current content hash
        self._embedded: Dict[str, str] = {}             # path -> hash stored in Chroma
        self._signature = self._embedding_signature()

    # ─── Embedding availability ───────────────────────

    @property
    def embeddings_available(self) -> bool:
        if self.embedding_manager is None or self.chroma_store is None:
            return False
        from ai.embeddings import NoOpEmbeddingAdapter
        return not isinstance(self.embedding_manager.adapter, NoOpEmbeddingAdapter)

    def _embedding_signature(self) -> str:
        if not self.embeddings_available:
            return "none"
        em = self.embedding_manager
        provider_cfg = em.providers_config.get(em.active_provider, {})
        inner = provider_cfg.get("config", provider_cfg)
        model = inner.get("model") or inner.get("default_model") or ""
        return f"{em.active_provider}:{model}"

    # ─── State persistence ───────────────────────────

    def _load_state(self) -> None:
        if not self.state_path or not self.state_path.exists():
            return
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            if data.get("embedding_signature") == self._signature:
                self._embedded = dict(data.get("embedded", {}))
            else:
                logger.info("Embedding provider changed — all notes will be re-embedded")
                self._embedded = {}
        except Exception as e:
            logger.warning(f"Could not read index state ({e}); starting fresh")
            self._embedded = {}

    def _save_state(self) -> None:
        if not self.state_path:
            return
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.state_path.with_suffix(".tmp")
            tmp.write_text(json.dumps({
                "embedding_signature": self._signature,
                "embedded": self._embedded,
            }, indent=1), encoding="utf-8")
            os.replace(tmp, self.state_path)
        except Exception as e:
            logger.warning(f"Could not save index state: {e}")

    # ─── Indexing ────────────────────────────────────

    async def full_sync(self) -> Dict[str, int]:
        """Chunk all cached notes; embed only notes whose content changed."""
        self._load_state()
        notes = self.vault_manager.notes_cache
        stats = {"notes": len(notes), "chunks": 0, "embedded": 0,
                 "unchanged": 0, "removed": 0}

        for path, note in notes.items():
            h = content_hash(note.content)
            self._seen[path] = h
            self.chunks[path] = chunk_note(note)
            stats["chunks"] += len(self.chunks[path])

            if not self.embeddings_available:
                continue
            if self._embedded.get(path) == h:
                stats["unchanged"] += 1
            elif await self._embed_note(path, note, h):
                stats["embedded"] += 1

        # Notes that disappeared while Aurora was offline
        for path in [p for p in self._embedded if p not in notes]:
            self._delete_from_chroma(path)
            self._embedded.pop(path, None)
            stats["removed"] += 1

        self._save_state()
        return stats

    async def index_note(self, path: str) -> bool:
        """Re-index one note. Returns False if its content didn't change."""
        note = self.vault_manager.notes_cache.get(path)
        if note is None:
            return self.remove_note(path)

        h = content_hash(note.content)
        if self._seen.get(path) == h:
            return False

        self._seen[path] = h
        self.chunks[path] = chunk_note(note)
        if self.embeddings_available and await self._embed_note(path, note, h):
            self._save_state()
        return True

    def remove_note(self, path: str) -> bool:
        """Drop a note from the index. Returns True if it was indexed."""
        existed = path in self._seen or path in self.chunks
        self._seen.pop(path, None)
        self.chunks.pop(path, None)
        if path in self._embedded:
            self._delete_from_chroma(path)
            self._embedded.pop(path, None)
            self._save_state()
        return existed

    async def _embed_note(self, path: str, note: Note, h: str) -> bool:
        chunks = self.chunks.get(path, [])
        try:
            if chunks:
                texts = [f"{c.metadata.get('heading', '')}\n{c.content}" for c in chunks]
                vectors = await self.embedding_manager.embed_texts(texts)
                self.chroma_store.update_note(note.id, chunks, vectors)
            else:
                self.chroma_store.delete_note(note.id)
            self._embedded[path] = h
            return True
        except Exception as e:
            # Leave _embedded untouched so the note is retried next sync
            logger.warning(f"Embedding failed for {path}: {e}")
            return False

    def _delete_from_chroma(self, path: str) -> None:
        try:
            note_id = str(uuid.uuid5(uuid.NAMESPACE_URL, path))
            self.chroma_store.delete_note(note_id)
        except Exception as e:
            logger.warning(f"Chroma delete failed for {path}: {e}")

    # ─── Search ──────────────────────────────────────

    def search_chunks(self, query: str, limit: int = 8) -> List[ChunkHit]:
        """Section-level keyword search across all chunks."""
        terms = query_terms(query)
        phrase = query.lower().strip()
        if not terms and not phrase:
            return []

        hits: List[ChunkHit] = []
        for path, chunks in self.chunks.items():
            for chunk in chunks:
                text = chunk.content.lower()
                heading = chunk.metadata.get("heading", "").lower()
                title = chunk.metadata.get("title", "").lower()

                score = 0.0
                matched = 0
                for t in terms:
                    in_text = min(text.count(t), 3)
                    in_head = t in heading
                    in_title = t in title
                    if in_text or in_head or in_title:
                        matched += 1
                    score += in_text + (2 if in_head else 0) + (3 if in_title else 0)

                if len(phrase) >= 4 and phrase in text:
                    score += 5
                if score <= 0:
                    continue
                # Reward chunks that cover more of the query's terms
                if terms:
                    score *= 0.5 + matched / len(terms)
                hits.append(ChunkHit(path=path, chunk=chunk, score=score))

        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:limit]

    async def semantic_search(self, query: str, limit: int = 8) -> List[ChunkHit]:
        """Vector search via ChromaDB (empty list when embeddings are unavailable)."""
        if not self.embeddings_available or not query.strip():
            return []
        try:
            vector = await self.embedding_manager.embed_single(query)
            results = self.chroma_store.query(vector, n_results=limit)
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            return []

        hits: List[ChunkHit] = []
        for r in results:
            meta = r.get("metadata") or {}
            path = meta.get("path")
            idx = meta.get("chunk_index")
            chunks = self.chunks.get(path, [])
            if path is None or idx is None or idx >= len(chunks):
                continue
            distance = r.get("distance") or 0.0
            hits.append(ChunkHit(path=path, chunk=chunks[idx], score=1.0 / (1.0 + distance)))
        return hits

    def get_stats(self) -> Dict[str, object]:
        return {
            "notes_indexed": len(self.chunks),
            "chunks": sum(len(c) for c in self.chunks.values()),
            "embeddings_available": self.embeddings_available,
            "embedding_signature": self._signature,
            "notes_embedded": len(self._embedded),
        }
