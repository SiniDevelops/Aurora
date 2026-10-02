"""
Settings API routes for Aurora backend.
Returns configuration info from aurora.yaml.
"""

from fastapi import APIRouter, Request, HTTPException

router = APIRouter()


@router.get("/")
async def get_settings(request: Request):
    """Get current Aurora configuration summary."""
    try:
        config = request.app.state.config
        llm_config = config.raw.get("llm", {})
        vault_config = config.raw.get("vault", {})
        privacy_config = config.raw.get("privacy", {})

        return {
            "llm": {
                "active_provider": llm_config.get("active_provider", "unknown"),
                "available_providers": list(llm_config.get("providers", {}).keys()),
            },
            "vault": {
                "path": vault_config.get("path", ""),
                "supported_extensions": vault_config.get("supported_extensions", []),
            },
            "privacy": {
                "enabled": privacy_config.get("enabled", True),
                "categories": privacy_config.get("enabled_categories", []),
            },
            "skills": {
                "loaded": [s.metadata.id for s in request.app.state.skill_registry.get_enabled_skills()]
                if hasattr(request.app.state, "skill_registry")
                else [],
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/llm/active")
async def get_active_provider(request: Request):
    """Get active LLM provider info."""
    try:
        llm_client = request.app.state.llm_client
        return {
            "active_provider": llm_client.get_active_provider(),
            "model_info": llm_client.get_model_info().model_dump()
            if hasattr(llm_client.get_model_info(), "model_dump")
            else str(llm_client.get_model_info()),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
