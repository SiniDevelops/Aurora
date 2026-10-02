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
    query: str
    limit: int = 10
    tags: Optional[List[str]] = None


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
                "word_count": len(note.content.split()) if note.content else 0,
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
    """Search vault notes."""
    try:
        vault_manager = request.app.state.vault_manager
        results = await vault_manager.search_notes(
            search_request.query, search_request.limit
        )
        return {
            "results": [
                {
                    "path": n.path,
                    "title": n.title,
                    "preview": n.content[:200] if n.content else "",
                    "tags": n.tags,
                }
                for n in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Re-index ─────────────────────────────────────────
@router.post("/index")
async def index_vault(request: Request):
    """Trigger full vault re-indexing."""
    try:
        vault_manager = request.app.state.vault_manager
        await vault_manager.initialize()
        return {"status": "success", "notes_indexed": len(vault_manager.notes_cache)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
