"""
Dashboard API routes for Aurora backend.
Returns aggregated vault statistics for the frontend dashboard.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/summary")
async def get_dashboard_summary(request: Request):
    """Aggregated dashboard data — stats, recent notes, graph info, skills."""
    vault = request.app.state.vault_manager
    graph = request.app.state.vault_graph
    backlinks = request.app.state.backlink_index
    config = request.app.state.config
    registry = request.app.state.skill_registry

    # ── Vault stats ────────────────────────────────
    stats = await vault.get_vault_stats()
    orphans = backlinks.get_orphan_notes()
    tags = await vault.get_all_tags()

    # ── Broken links (outgoing links whose target doesn't resolve) ────
    broken = 0
    for note in vault.notes_cache.values():
        for link in note.links:
            target = link.get("target", "")
            # Check if any note matches (by title or path stem)
            target_lower = target.lower().split("#")[0].strip()
            found = any(
                n.title.lower() == target_lower
                or n.path.lower().replace(".md", "") == target_lower
                or n.path.lower().endswith(f"/{target_lower}.md")
                for n in vault.notes_cache.values()
            )
            if not found:
                broken += 1

    # ── Recent notes ──────────────────────────────
    recent = await vault.get_recent_notes(limit=8)
    now = datetime.now()
    recent_list = []
    for n in recent:
        delta = now - n.modified_at
        if delta.days > 0:
            ago = f"{delta.days}d ago"
        elif delta.seconds >= 3600:
            ago = f"{delta.seconds // 3600}h ago"
        elif delta.seconds >= 60:
            ago = f"{delta.seconds // 60}m ago"
        else:
            ago = "just now"
        recent_list.append({
            "path": n.path,
            "title": n.title,
            "modified_ago": ago,
        })

    # ── Most connected notes ─────────────────────
    top_connected = graph.get_most_connected(n=5)

    # ── Top tags ─────────────────────────────────
    sorted_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)[:10]

    # ── Folder distribution ──────────────────────
    folder_counts: dict[str, int] = {}
    for note in vault.notes_cache.values():
        folder = note.folder or "/"
        root = folder.split("/")[0] if "/" in folder else folder
        folder_counts[root] = folder_counts.get(root, 0) + 1

    # ── Skills ───────────────────────────────────
    skills_list = [
        {
            "id": s.metadata.id,
            "name": s.metadata.name,
            "description": s.metadata.description,
            "examples": s.metadata.examples[:2] if s.metadata.examples else [],
        }
        for s in registry.get_enabled_skills()
    ]

    # ── LLM info ─────────────────────────────────
    llm_config = config.raw.get("llm", {})
    active_provider = llm_config.get("active_provider", "unknown")
    provider_cfg = llm_config.get("providers", {}).get(active_provider, {})
    inner_cfg = provider_cfg.get("config", provider_cfg)
    model_name = inner_cfg.get("default_model", provider_cfg.get("model", "unknown"))

    return {
        "stats": {
            "total_notes": stats["total_notes"],
            "total_words": stats["total_words"],
            "total_tags": stats["total_tags"],
            "total_links": stats["total_links"],
            "orphan_notes": len(orphans),
            "broken_links": broken,
        },
        "graph": {
            "nodes": len(graph.nodes),
            "edges": len(graph.directed_edges),
        },
        "recent_notes": recent_list,
        "most_connected": top_connected[:5],
        "top_tags": [{"tag": t, "count": c} for t, c in sorted_tags],
        "folder_distribution": folder_counts,
        "llm": {
            "provider": active_provider,
            "model": model_name,
        },
        "skills": skills_list,
    }
