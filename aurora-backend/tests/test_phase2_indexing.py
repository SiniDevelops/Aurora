"""
Tests for Phase 2 indexing: heading chunker (A6), incremental indexer (A4),
and graph-aware context builder (A5).

Run: .\\venv\\Scripts\\python.exe -m pytest tests/test_phase2_indexing.py -v
"""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.vault_manager import VaultManager
from core.chunker import chunk_note
from core.indexer import VaultIndexer, query_terms
from core.backlink_index import BacklinkIndex
from core.vault_graph import VaultGraph
from core.context_builder import ContextBuilder


def run(coro):
    return asyncio.run(coro)


LONG_PARA = "Sleep consolidates memory and supports learning. " * 12

NOTES = {
    "Projects/Alpha.md": f"""---
title: Project Alpha
tags: [project]
---
Intro paragraph about Project Alpha and why it exists in the first place for the team.

## Goals
Ship the search feature. Improve retrieval quality using ChromaDB and better chunking of notes.

## Risks
Rate limits on the Gemini free tier may slow down testing and evaluation of the assistant.

```python
# Not a heading — inside a code fence
x = 1
```

### Mitigation
Retry with exponential backoff when the provider returns a 429 response code to the client.

See [[Python]] and [[ChromaDB]].
""",
    "Resources/Python.md": "# Python\nPython is the backend language used for the FastAPI server and all skills. [[Project Alpha]]\n",
    "Resources/ChromaDB.md": "# ChromaDB\nChromaDB is the vector database that stores embeddings for semantic search. [[Project Alpha]]\n",
    "Inbox/Sleep.md": f"# Sleep\n\n{LONG_PARA}\n\n{LONG_PARA}\n\n{LONG_PARA}\n\n{LONG_PARA}\n",
    "Inbox/Unrelated.md": "# Cooking\nA recipe for lentil soup with cumin and lemon.\n",
}


def make_vault(tmp: str) -> VaultManager:
    for rel, content in NOTES.items():
        p = Path(tmp) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    vm = VaultManager(tmp, excluded_folders=[], supported_extensions=[".md"])
    run(vm.initialize())
    return vm


# ─── A6: Chunker ─────────────────────────────────────

def test_chunker_splits_by_headings_and_ignores_code_fences():
    with tempfile.TemporaryDirectory() as tmp:
        vm = make_vault(tmp)
        chunks = chunk_note(vm.notes_cache["Projects/Alpha.md"])
        headings = [c.metadata["heading"] for c in chunks]

        assert "Project Alpha > Goals" in headings
        assert "Project Alpha > Risks" in headings
        assert "Project Alpha > Risks > Mitigation" in headings
        # Code-fence comment must not become a heading
        assert not any("Not a heading" in h for h in headings)
        # Frontmatter excluded from chunk text
        assert not any("tags:" in c.content for c in chunks)
        # Indices are sequential
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_chunker_splits_oversized_sections():
    with tempfile.TemporaryDirectory() as tmp:
        vm = make_vault(tmp)
        chunks = chunk_note(vm.notes_cache["Inbox/Sleep.md"])
        assert len(chunks) >= 2
        assert all(c.token_count <= 400 for c in chunks)
        # H1 "# Sleep" repeats the title → not duplicated in the heading path
        assert all(c.metadata["heading"] == "Sleep" for c in chunks)


def test_query_terms_drops_stopwords():
    assert query_terms("What did I write about the Gemini rate limits?") == ["gemini", "rate", "limits"]


# ─── A4: Incremental indexer ─────────────────────────

def test_indexer_detects_real_changes_only():
    with tempfile.TemporaryDirectory() as tmp:
        vm = make_vault(tmp)
        idx = VaultIndexer(vm, state_path=os.path.join(tmp, "state.json"))
        stats = run(idx.full_sync())
        assert stats["notes"] == len(NOTES)
        assert stats["chunks"] > len(NOTES)

        # Same content re-read → not a change
        run(vm.refresh_note("Resources/Python.md"))
        assert run(idx.index_note("Resources/Python.md")) is False

        # Real edit → change, chunks updated
        p = Path(tmp) / "Resources/Python.md"
        p.write_text(p.read_text(encoding="utf-8") + "\n## Typing\nPython supports type hints via mypy.\n",
                     encoding="utf-8")
        run(vm.refresh_note("Resources/Python.md"))
        assert run(idx.index_note("Resources/Python.md")) is True
        assert any("Typing" in c.metadata["heading"] for c in idx.chunks["Resources/Python.md"])

        # Deletion
        vm.notes_cache.pop("Inbox/Unrelated.md")
        assert idx.remove_note("Inbox/Unrelated.md") is True
        assert "Inbox/Unrelated.md" not in idx.chunks
        assert idx.remove_note("Inbox/Unrelated.md") is False


class FakeEmbeddings:
    """Embedding manager stand-in that counts how many texts get embedded."""

    def __init__(self):
        self.active_provider = "fake"
        self.providers_config = {"fake": {"config": {"model": "v1"}}}
        self.adapter = object()  # not a NoOp adapter → embeddings 'available'
        self.embedded = 0

    async def embed_texts(self, texts):
        self.embedded += len(texts)
        return [[float(len(t)), 1.0, 0.0] for t in texts]

    async def embed_single(self, text):
        return [float(len(text)), 1.0, 0.0]


class FakeChroma:
    def __init__(self):
        self.store = {}

    def update_note(self, note_id, chunks, vectors):
        self.store[note_id] = (chunks, vectors)

    def delete_note(self, note_id):
        self.store.pop(note_id, None)

    def query(self, vector, n_results=5, where=None):
        return []


def test_indexer_only_reembeds_changed_notes_across_restarts():
    with tempfile.TemporaryDirectory() as tmp:
        state = os.path.join(tmp, "state.json")
        vm = make_vault(tmp)
        emb, chroma = FakeEmbeddings(), FakeChroma()

        first = run(VaultIndexer(vm, chroma, emb, state).full_sync())
        assert first["embedded"] == len(NOTES)
        assert json.loads(Path(state).read_text())["embedding_signature"] == "fake:v1"

        # "Restart" with nothing changed → nothing re-embedded
        emb.embedded = 0
        second = run(VaultIndexer(vm, chroma, emb, state).full_sync())
        assert second["embedded"] == 0 and second["unchanged"] == len(NOTES)
        assert emb.embedded == 0

        # Edit one note offline, delete another, restart
        p = Path(tmp) / "Inbox/Unrelated.md"
        p.write_text("# Cooking\nNow with chickpeas.\n", encoding="utf-8")
        (Path(tmp) / "Resources/ChromaDB.md").unlink()
        vm.notes_cache.clear()
        run(vm.initialize())
        third = run(VaultIndexer(vm, chroma, emb, state).full_sync())
        assert third["embedded"] == 1
        assert third["removed"] == 1

        # Switching embedding model forces a full re-embed
        emb.providers_config["fake"]["config"]["model"] = "v2"
        fourth = run(VaultIndexer(vm, chroma, emb, state).full_sync())
        assert fourth["embedded"] == len(vm.notes_cache)


# ─── A5: Graph-aware context ─────────────────────────

def build_ctx_builder(vm):
    idx = VaultIndexer(vm)
    run(idx.full_sync())
    bl = BacklinkIndex()
    bl.rebuild_index(vm.notes_cache)
    graph = VaultGraph()
    graph.build_graph(vm.notes_cache, bl)
    return ContextBuilder(vm, None, None, indexer=idx, graph_getter=lambda: graph)


def test_context_returns_relevant_sections_not_whole_note():
    with tempfile.TemporaryDirectory() as tmp:
        vm = make_vault(tmp)
        cb = build_ctx_builder(vm)
        ctx = run(cb.build_context("How do we handle Gemini rate limits?"))

        assert ctx.notes, "natural-language query should find something"
        top = ctx.notes[0]
        assert top.path == "Projects/Alpha.md"
        assert "Rate limits" in top.content
        # Original cache untouched (we work on copies)
        assert "title: Project Alpha" in vm.notes_cache["Projects/Alpha.md"].content


def test_context_includes_graph_neighbours():
    with tempfile.TemporaryDirectory() as tmp:
        vm = make_vault(tmp)
        cb = build_ctx_builder(vm)
        ctx = run(cb.build_context("project goals and risks mitigation"))

        primary = {n.path for n in ctx.notes}
        linked = {n.path for n in ctx.linked_notes}
        assert "Projects/Alpha.md" in primary
        # Alpha links to Python and ChromaDB → they should come in as linked notes
        assert {"Resources/Python.md", "Resources/ChromaDB.md"} & (linked | primary)
        assert not (primary & linked), "a note must not appear twice"
        for path in linked:
            assert "Project Alpha" in ctx.linked_via[path]


def test_context_respects_token_budget():
    with tempfile.TemporaryDirectory() as tmp:
        vm = make_vault(tmp)
        cb = build_ctx_builder(vm)
        ctx = run(cb.build_context("sleep memory learning project python", max_tokens=300))
        total = sum(len(n.content) // 4 for n in ctx.notes + ctx.linked_notes)
        assert total <= 300
