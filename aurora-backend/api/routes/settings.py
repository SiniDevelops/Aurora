"""
Settings API routes for Aurora backend.
GET returns current config; PUT saves changes to aurora.yaml.
"""

import os
import importlib
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger("aurora.settings")


@router.get("/")
async def get_settings(request: Request):
    """Get current Aurora configuration summary."""
    try:
        config = request.app.state.config
        llm_config = config.raw.get("llm", {})
        vault_config = config.raw.get("vault", {})
        privacy_config = config.raw.get("privacy", {})
        skills_config = config.raw.get("skills", {})

        # Provider info (never return actual keys)
        providers_info = {}
        for name, pcfg in llm_config.get("providers", {}).items():
            # Keys are under providers.{name}.config.api_key
            inner_cfg = pcfg.get("config", pcfg)
            api_key_ref = inner_cfg.get("api_key", "")
            has_key = bool(api_key_ref) and api_key_ref != ""
            # Check if the env var is actually set
            if isinstance(api_key_ref, str) and api_key_ref.startswith("${"):
                env_var = api_key_ref.strip("${}").split(":")[0]
                has_key = bool(os.environ.get(env_var))
            # Model is under config.default_model
            model = inner_cfg.get("default_model", pcfg.get("model", ""))
            providers_info[name] = {
                "model": model,
                "has_key": has_key,
            }

        # Per-skill info
        builtin_cfg = skills_config.get("builtin", {})
        skills_list = []
        registry = getattr(request.app.state, "skill_registry", None)
        for skill_id, scfg in builtin_cfg.items():
            skill = registry.get_skill(skill_id) if registry else None
            skills_list.append({
                "id": skill_id,
                "name": skill.metadata.name if skill else skill_id.replace("_", " ").title(),
                "description": skill.metadata.description if skill else "",
                "enabled": scfg.get("enabled", False),
            })

        return {
            "llm": {
                "active_provider": llm_config.get("active_provider", "unknown"),
                "available_providers": list(llm_config.get("providers", {}).keys()),
                "providers": providers_info,
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
                "loaded": [s.metadata.id for s in registry.get_enabled_skills()] if registry else [],
                "all": skills_list,
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


# ─── PUT: Save settings ─────────────────────────────

class SettingsUpdate(BaseModel):
    llm_active_provider: Optional[str] = None
    privacy_enabled: Optional[bool] = None
    privacy_categories: Optional[List[str]] = None
    skills_enabled: Optional[Dict[str, bool]] = None  # {skill_id: enabled}
    vault_path: Optional[str] = None


@router.put("/")
async def update_settings(request: Request, update: SettingsUpdate):
    """
    Apply partial settings updates to aurora.yaml.
    Returns which changes were applied and whether a restart is required.
    """
    from utils.yaml_editor import edit_yaml_value

    config = request.app.state.config
    yaml_path = config.config_path if hasattr(config, "config_path") else "aurora.yaml"

    # Fall back to finding the yaml file
    if not os.path.isabs(yaml_path):
        # Look in project root (one level up from aurora-backend)
        candidates = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", yaml_path),
            os.path.join(os.getcwd(), yaml_path),
            os.path.join(os.getcwd(), "..", yaml_path),
        ]
        for c in candidates:
            if os.path.exists(c):
                yaml_path = os.path.abspath(c)
                break

    if not os.path.exists(yaml_path):
        raise HTTPException(status_code=500, detail=f"Config file not found: {yaml_path}")

    applied = []
    restart_required = False
    errors = []

    # 1. LLM provider
    if update.llm_active_provider is not None:
        available = list(config.raw.get("llm", {}).get("providers", {}).keys())
        if update.llm_active_provider not in available:
            errors.append(f"Unknown provider '{update.llm_active_provider}'. Available: {available}")
        else:
            ok = edit_yaml_value(yaml_path, ["llm", "active_provider"], update.llm_active_provider)
            if ok:
                applied.append("llm.active_provider")
                restart_required = True

    # 2. Privacy enabled
    if update.privacy_enabled is not None:
        ok = edit_yaml_value(yaml_path, ["privacy", "enabled"], update.privacy_enabled)
        if ok:
            applied.append("privacy.enabled")
            restart_required = True

    # 3. Privacy categories
    if update.privacy_categories is not None:
        ok = edit_yaml_value(yaml_path, ["privacy", "enabled_categories"], update.privacy_categories)
        if ok:
            applied.append("privacy.enabled_categories")
            restart_required = True

    # 4. Skills enable/disable
    if update.skills_enabled:
        registry = request.app.state.skill_registry
        builtin_cfg = config.raw.get("skills", {}).get("builtin", {})
        for skill_id, enabled in update.skills_enabled.items():
            if skill_id not in builtin_cfg:
                errors.append(f"Unknown skill: {skill_id}")
                continue
            ok = edit_yaml_value(yaml_path, ["skills", "builtin", skill_id, "enabled"], enabled)
            if ok:
                applied.append(f"skills.{skill_id}.enabled")
                # Apply at runtime
                if enabled and not registry.get_skill(skill_id):
                    # Try to load and register the skill
                    try:
                        module = importlib.import_module("skills.builtin")
                        class_name = "".join(w.capitalize() for w in skill_id.split("_")) + "Skill"
                        skill_class = getattr(module, class_name)
                        skill_instance = skill_class(
                            request.app.state.vault_manager,
                            request.app.state.llm_client,
                            logger,
                        )
                        registry.register(skill_instance)
                    except Exception as e:
                        errors.append(f"Skill {skill_id} enabled in YAML but failed to load: {e}")
                elif not enabled and registry.get_skill(skill_id):
                    # Unregister
                    registry._skills.pop(skill_id, None)

    # 5. Vault path
    if update.vault_path is not None:
        if not os.path.isdir(update.vault_path):
            errors.append(f"Directory does not exist: {update.vault_path}")
        else:
            ok = edit_yaml_value(yaml_path, ["vault", "path"], update.vault_path)
            if ok:
                applied.append("vault.path")
                restart_required = True

    status = "ok" if not errors else "partial" if applied else "error"
    return {
        "status": status,
        "applied": applied,
        "restart_required": restart_required,
        "errors": errors,
        "message": (
            f"Applied {len(applied)} change(s)."
            + (" Restart required for some changes." if restart_required else "")
            + (f" {len(errors)} error(s)." if errors else "")
        ),
    }
