"""
Vault API routes for Aurora backend.
Provides endpoints for browsing, searching, and managing vault notes.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import urllib.parse

router = APIRouter()


class CreateNoteRequest(BaseModel):
    path: str
    content: str
    frontmatter: Optional[Dict[str, Any]] = None


class UpdateNoteRequest(BaseModel):
    content: str
    frontmatter: Optional[Dict[str, Any]] = None


class SearchRequest(BaseModel):
    query: str = ""
    limit: int = 10
    tags: Optional[List[str]] = None          # note must carry ALL of these tags
    folder: Optional[str] = None              # any depth, e.g. "Projects/AI"
    date_from: Optional[str] = None           # "YYYY-MM-DD" inclusive
    date_to: Optional[str] = None             # "YYYY-MM-DD" inclusive
    date_field: str = "modified"              # "modified" | "created"
    include_sections: bool = True             # attach best-matching sections


def _parse_day(value: Optional[str]):
    if not value:
        return None
    from datetime import date
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date '{value}', expected YYYY-MM-DD")


def _note_matches_filters(note, tags, folder, day_from, day_to, date_field) -> bool:
    if tags:
        note_tags = {t.lower().lstrip("#") for t in note.tags}
        if not all(t.lower().lstrip("#") in note_tags for t in tags):
            return False
    if folder:
        prefix = folder.replace("\\", "/").strip("/") + "/"
        if not note.path.replace("\\", "/").startswith(prefix):
            return False
    if day_from or day_to:
        stamp = note.created_at if date_field == "created" else note.modified_at
        day = stamp.date()
        if day_from and day < day_from:
            return False
        if day_to and day > day_to:
            return False
    return True


def _snippet(text: str, query: str, width: int = 180) -> str:
    """Return a short excerpt of text centred on the first query term."""
    flat = " ".join(text.split())
    lower = flat.lower()
    pos = -1
    for term in [query.lower().strip()] + query.lower().split():
        if term and (pos := lower.find(term)) >= 0:
            break
    if pos < 0:
        return flat[:width] + ("…" if len(flat) > width else "")
    start = max(0, pos - width // 3)
    end = min(len(flat), start + width)
    return ("…" if start > 0 else "") + flat[start:end] + ("…" if end < len(flat) else "")


# ─── List all notes ──────────────────────────────────
@router.get("/notes")
async def list_notes(request: Request):
    """List all indexed notes with basic metadata."""
    try:
        vault_manager = request.app.state.vault_manager
        notes = []
        for path, note in vault_manager.notes_cache.items():
            notes.append({
                "path": note.path,
                "title": note.title,
                "tags": note.tags,
                "folder": note.folder,
                "word_count": len(note.content.split()) if note.content else 0,
                "created_at": note.created_at.isoformat(),
                "modified_at": note.modified_at.isoformat(),
            })
        return notes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Vault folder tree ───────────────────────────────
@router.get("/tree")
async def get_tree(request: Request):
    """Get vault folder/file structure."""
    try:
        vault_manager = request.app.state.vault_manager
        tree = await vault_manager.get_vault_tree()
        return {"tree": tree, "total_notes": len(vault_manager.notes_cache)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Tags ─────────────────────────────────────────────
@router.get("/tags")
async def get_tags(request: Request):
    """Get all tags with counts."""
    try:
        vault_manager = request.app.state.vault_manager
        tags = await vault_manager.get_all_tags()
        return tags
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Vault stats ─────────────────────────────────────
@router.get("/stats")
async def get_stats(request: Request):
    """Get vault statistics."""
    try:
        vault_manager = request.app.state.vault_manager
        stats = await vault_manager.get_vault_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Get single note ─────────────────────────────────
@router.get("/note/{path:path}")
async def get_note(request: Request, path: str):
    """Get a specific note by path."""
    try:
        decoded_path = urllib.parse.unquote(path)
        vault_manager = request.app.state.vault_manager
        note = await vault_manager.read_note(decoded_path)
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")
        return {
            "path": note.path,
            "title": note.title,
            "content": note.content,
            "tags": note.tags,
            "links": note.links,
            "frontmatter": note.frontmatter,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Create note ─────────────────────────────────────
@router.post("/note")
async def create_note(request: Request, note_request: CreateNoteRequest):
    """Create a new note."""
    try:
        vault_manager = request.app.state.vault_manager
        note = await vault_manager.write_note(
            note_request.path, note_request.content, note_request.frontmatter
        )
        return {"status": "success", "path": note.path, "title": note.title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Update note ─────────────────────────────────────
@router.put("/note/{path:path}")
async def update_note(request: Request, path: str, note_request: UpdateNoteRequest):
    """Update an existing note."""
    try:
        decoded_path = urllib.parse.unquote(path)
        vault_manager = request.app.state.vault_manager
        note = await vault_manager.write_note(
            decoded_path, note_request.content, note_request.frontmatter
        )
        return {"status": "success", "path": note.path, "title": note.title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Delete note ─────────────────────────────────────
@router.delete("/note/{path:path}")
async def delete_note(request: Request, path: str):
    """Delete a note."""
    try:
        decoded_path = urllib.parse.unquote(path)
        vault_manager = request.app.state.vault_manager
        await vault_manager.delete_note(decoded_path)
        return {"status": "success", "message": "Note deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Search ───────────────────────────────────────────
@router.post("/search")
async def search_vault(request: Request, search_request: SearchRequest):
    """Search vault notes with optional tag / folder / date-range filters.

    An empty query with filters returns all matching notes (newest first).
    When include_sections is set, each result carries its best-matching
    heading sections from the chunk index.
    """
    try:
        state = request.app.state
        vault_manager = state.vault_manager
        req = search_request
        query = (req.query or "").strip()
        day_from, day_to = _parse_day(req.date_from), _parse_day(req.date_to)
        date_field = "created" if req.date_field == "created" else "modified"

        if query:
            candidates = await vault_manager.search_notes(query, len(vault_manager.notes_cache) or 1)
        else:
            candidates = sorted(vault_manager.notes_cache.values(), key=lambda n: n.modified_at, reverse=True)

        filtered = [n for n in candidates
                    if _note_matches_filters(n, req.tags, req.folder, day_from, day_to, date_field)]

        # Section hits (also lets notes match on section text the plain search missed)
        sections_by_path: dict = {}
        indexer = getattr(state, "indexer", None)
        if query and req.include_sections and indexer is not None:
            for hit in indexer.search_chunks(query, limit=200):
                bucket = sections_by_path.setdefault(hit.path, [])
                if len(bucket) < 3:
                    bucket.append({
                        "heading": hit.chunk.metadata.get("heading", ""),
                        "snippet": _snippet(hit.chunk.content, query),
                        "score": round(hit.score, 2),
                    })
            seen = {n.path for n in filtered}
            for path in sections_by_path:
                note = vault_manager.notes_cache.get(path)
                if note and path not in seen and _note_matches_filters(
                        note, req.tags, req.folder, day_from, day_to, date_field):
                    filtered.append(note)
                    seen.add(path)

        total = len(filtered)
        results = filtered[: max(1, req.limit)]
        return {
            "total": total,
            "results": [
                {
                    "path": n.path,
                    "title": n.title,
                    "preview": _snippet(n.clean_content or n.content or "", query) if query
                               else (n.clean_content or n.content or "")[:200],
                    "tags": n.tags,
                    "folder": n.folder,
                    "word_count": n.word_count or (len(n.content.split()) if n.content else 0),
                    "created_at": n.created_at.isoformat(),
                    "modified_at": n.modified_at.isoformat(),
                    "sections": sections_by_path.get(n.path, []),
                }
                for n in results
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Re-index ─────────────────────────────────────────
@router.post("/index")
async def index_vault(request: Request):
    """Trigger a full vault re-scan. Only changed notes are re-embedded."""
    try:
        from core.backlink_index import BacklinkIndex
        from core.vault_graph import VaultGraph

        state = request.app.state
        vault_manager = state.vault_manager
        vault_manager.notes_cache.clear()  # drop notes deleted while the watcher was off
        await vault_manager.initialize()

        stats = {}
        indexer = getattr(state, "indexer", None)
        if indexer is not None:
            stats = await indexer.full_sync()

        backlinks = BacklinkIndex()
        backlinks.rebuild_index(vault_manager.notes_cache)
        graph = VaultGraph()
        graph.build_graph(vault_manager.notes_cache, backlinks)
        state.backlink_index = backlinks
        state.vault_graph = graph

        return {
            "status": "success",
            "notes_indexed": len(vault_manager.notes_cache),
            **stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/index/stats")
async def index_stats(request: Request):
    """Chunk index / embedding status."""
    indexer = getattr(request.app.state, "indexer", None)
    if indexer is None:
        raise HTTPException(status_code=503, detail="Indexer not initialized")
    return indexer.get_stats()


@router.get("/search/sections")
async def search_sections(request: Request, q: str, limit: int = 10):
    """Section-level search: returns the matching heading sections, not whole notes."""
    indexer = getattr(request.app.state, "indexer", None)
    if indexer is None:
        raise HTTPException(status_code=503, detail="Indexer not initialized")
    hits = indexer.search_chunks(q, limit=limit)
    return {
        "query": q,
        "results": [
            {
                "path": h.path,
                "title": h.chunk.metadata.get("title", ""),
                "heading": h.chunk.metadata.get("heading", ""),
                "heading_path": h.chunk.heading_path,
                "snippet": h.chunk.content[:300],
                "score": round(h.score, 2),
            }
            for h in hits
        ],
    }


# ─── Knowledge Graph ──────────────────────────────────
@router.get("/graph")
async def get_vault_graph(request: Request):
    """Return the knowledge graph as D3.js-compatible JSON."""
    try:
        vault_graph = request.app.state.vault_graph
        return vault_graph.to_json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backlinks/{path:path}")
async def get_backlinks(path: str, request: Request):
    """Get all backlinks for a given note."""
    try:
        backlink_index = request.app.state.backlink_index
        decoded_path = urllib.parse.unquote(path)
        backlinks = backlink_index.get_backlinks(decoded_path)
        return {
            "path": decoded_path,
            "backlinks": [
                {
                    "source": bl.source_path,
                    "context": bl.context_snippet,
                    "link_text": bl.link_text,
                }
                for bl in backlinks
            ],
            "count": len(backlinks),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orphans")
async def get_orphan_notes(request: Request):
    """Get notes with no inlinks or outlinks."""
    try:
        backlink_index = request.app.state.backlink_index
        orphans = backlink_index.get_orphan_notes()
        return {"orphans": orphans, "count": len(orphans)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
