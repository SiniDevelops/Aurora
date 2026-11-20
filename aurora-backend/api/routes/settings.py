"""
Settings API routes for Aurora backend.
GET returns current config; PUT saves changes to aurora.yaml and applies
runtime updates where possible.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger("aurora.settings")

DEFAULT_PRIVACY_CATEGORIES = [
    "person_name",
    "email",
    "phone",
    "address",
    "credit_card",
    "api_key",
    "ip_address",
]


def _resolve_yaml_path(config) -> str:
    """Resolve the absolute path to aurora.yaml."""
    raw_path = getattr(config, "_config_path", None) or getattr(config, "config_path", "aurora.yaml")
    yaml_path = str(raw_path)
    if os.path.isabs(yaml_path) and os.path.exists(yaml_path):
        return yaml_path

    candidates = [
        yaml_path,
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "aurora.yaml"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "aurora.yaml"),
        os.path.join(os.getcwd(), "aurora.yaml"),
        os.path.join(os.getcwd(), "..", "aurora.yaml"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    raise HTTPException(status_code=500, detail=f"Config file not found: {yaml_path}")


def _build_settings_response(request: Request) -> Dict[str, Any]:
    config = request.app.state.config
    llm_config = config.raw.get("llm", {})
    vault_config = config.raw.get("vault", {})
    privacy_config = config.raw.get("privacy", {})
    skills_config = config.raw.get("skills", {})

    # Provider info (never return actual keys)
    providers_info = {}
    for name, pcfg in llm_config.get("providers", {}).items():
        inner_cfg = pcfg.get("config", pcfg)
        is_local = name == "ollama"
        if is_local:
            has_key = bool(inner_cfg.get("base_url"))
        else:
            api_key_ref = inner_cfg.get("api_key", "")
            has_key = bool(api_key_ref)
            if isinstance(api_key_ref, str) and api_key_ref.startswith("${"):
                env_var = api_key_ref.strip("${}").split(":")[0]
                has_key = bool(os.environ.get(env_var))
        model = inner_cfg.get("default_model", pcfg.get("model", ""))
        providers_info[name] = {
            "model": model,
            "has_key": has_key,
            "local": is_local,
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
            "enabled": bool(scfg.get("enabled", False)),
        })

    enabled_cats = list(privacy_config.get("enabled_categories", []))
    all_cats = list(DEFAULT_PRIVACY_CATEGORIES)
    for cat in enabled_cats:
        if cat not in all_cats:
            all_cats.append(cat)

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
            "enabled": bool(privacy_config.get("enabled", True)),
            "categories": enabled_cats,
            "all_categories": all_cats,
        },
        "skills": {
            "loaded": [s.metadata.id for s in registry.get_enabled_skills()] if registry else [],
            "all": skills_list,
        },
    }


@router.get("/")
async def get_settings(request: Request):
    """Get current Aurora configuration summary."""
    try:
        return _build_settings_response(request)
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
    llm_model: Optional[str] = None
    privacy_enabled: Optional[bool] = None
    privacy_categories: Optional[List[str]] = None
    skills_enabled: Optional[Dict[str, bool]] = None  # {skill_id: enabled}
    vault_path: Optional[str] = None


@router.put("/")
async def update_settings(request: Request, update: SettingsUpdate):
    """
    Apply partial settings updates to aurora.yaml and reload config.
    Returns which changes were applied, whether a restart is required,
    and the updated settings snapshot.
    """
    from utils.yaml_editor import edit_yaml_value

    config = request.app.state.config
    yaml_path = _resolve_yaml_path(config)

    applied: List[str] = []
    restart_required = False
    errors: List[str] = []

    llm_cfg = config.raw.get("llm", {})
    available_providers = list(llm_cfg.get("providers", {}).keys())
    current_provider = llm_cfg.get("active_provider", "")
    target_provider = current_provider
    llm_changed = False

    # 1. LLM provider
    if update.llm_active_provider is not None and update.llm_active_provider != current_provider:
        if update.llm_active_provider not in available_providers:
            errors.append(
                f"Unknown provider '{update.llm_active_provider}'. Available: {available_providers}"
            )
        else:
            ok = edit_yaml_value(yaml_path, ["llm", "active_provider"], update.llm_active_provider)
            if ok:
                applied.append("llm.active_provider")
                target_provider = update.llm_active_provider
                llm_changed = True
            else:
                errors.append("Failed to update llm.active_provider in aurora.yaml")

    # 2. Active provider's default model
    if update.llm_model is not None:
        cleaned_model = update.llm_model.strip()
        if not cleaned_model:
            errors.append("Model name cannot be empty")
        elif target_provider in available_providers:
            cur_model = llm_cfg.get("providers", {}).get(target_provider, {}).get("config", {}).get("default_model", "")
            if cleaned_model != cur_model:
                ok = edit_yaml_value(
                    yaml_path,
                    ["llm", "providers", target_provider, "config", "default_model"],
                    cleaned_model,
                )
                if ok:
                    applied.append(f"llm.providers.{target_provider}.default_model")
                    llm_changed = True
                else:
                    errors.append(f"Failed to update default_model for '{target_provider}'")

    # 3. Privacy enabled
    if update.privacy_enabled is not None:
        cur_enabled = bool(config.raw.get("privacy", {}).get("enabled", True))
        if update.privacy_enabled != cur_enabled:
            ok = edit_yaml_value(yaml_path, ["privacy", "enabled"], update.privacy_enabled)
            if ok:
                applied.append("privacy.enabled")
                restart_required = True
            else:
                errors.append("Failed to update privacy.enabled")

    # 4. Privacy categories
    if update.privacy_categories is not None:
        cur_cats = list(config.raw.get("privacy", {}).get("enabled_categories", []))
        if update.privacy_categories != cur_cats:
            ok = edit_yaml_value(yaml_path, ["privacy", "enabled_categories"], update.privacy_categories)
            if ok:
                applied.append("privacy.enabled_categories")
                sanitizer = getattr(request.app.state, "sanitizer", None)
                if sanitizer is not None and hasattr(sanitizer, "detector"):
                    sanitizer.detector.enabled_categories = [c.upper() for c in update.privacy_categories]
            else:
                errors.append("Failed to update privacy.enabled_categories")

    # 5. Skills enable/disable
    if update.skills_enabled:
        registry = getattr(request.app.state, "skill_registry", None)
        builtin_cfg = config.raw.get("skills", {}).get("builtin", {})
        for skill_id, enabled in update.skills_enabled.items():
            if skill_id not in builtin_cfg:
                errors.append(f"Unknown skill: {skill_id}")
                continue
            cur_skill_enabled = bool(builtin_cfg[skill_id].get("enabled", False))
            if enabled == cur_skill_enabled and (
                registry is None or bool(registry.get_skill(skill_id)) == enabled
            ):
                continue
            ok = edit_yaml_value(yaml_path, ["skills", "builtin", skill_id, "enabled"], enabled)
            if ok:
                applied.append(f"skills.{skill_id}.enabled")
                if registry is not None:
                    if enabled and not registry.get_skill(skill_id):
                        try:
                            await registry.load_and_register(
                                skill_id,
                                request.app.state.vault_manager,
                                request.app.state.llm_client,
                                logger,
                            )
                        except Exception as e:
                            errors.append(f"Skill {skill_id} enabled in YAML but failed to load: {e}")
                    elif not enabled and registry.get_skill(skill_id):
                        registry.unregister(skill_id)
            else:
                errors.append(f"Failed to update skills.{skill_id}.enabled")

    # 6. Vault path (skip if unchanged so ${AURORA_VAULT_PATH} isn't clobbered)
    if update.vault_path is not None:
        cleaned_path = update.vault_path.strip()
        current_vault = config.raw.get("vault", {}).get("path", "")
        if cleaned_path != current_vault:
            if not os.path.isdir(cleaned_path):
                errors.append(f"Directory does not exist: {cleaned_path}")
            else:
                ok = edit_yaml_value(yaml_path, ["vault", "path"], cleaned_path)
                if ok:
                    applied.append("vault.path")
                    restart_required = True
                else:
                    errors.append("Failed to update vault.path")

    # Reload config from disk so GET /api/settings/ immediately reflects edits
    if applied:
        try:
            config.reload()
        except Exception as e:
            errors.append(f"Saved YAML but failed to reload config: {e}")
            restart_required = True

    # Attempt live hot-swap of LLM provider / model after config reload
    if llm_changed:
        llm_client = getattr(request.app.state, "llm_client", None)
        if llm_client is not None and hasattr(llm_client, "switch_provider"):
            try:
                new_pcfg = config.raw.get("llm", {}).get("providers", {}).get(target_provider, {})
                llm_client.switch_provider(target_provider, new_pcfg)
            except Exception as e:
                logger.warning(f"LLM hot-swap to '{target_provider}' failed (will apply on restart): {e}")
                restart_required = True
        else:
            restart_required = True

    status = "ok" if not errors else "partial" if applied else "error"
    return {
        "status": status,
        "applied": applied,
        "restart_required": restart_required,
        "errors": errors,
        "settings": _build_settings_response(request),
        "message": (
            ("No changes to save." if not applied and not errors else f"Saved {len(applied)} change(s).")
            + (" Restart backend to apply all changes." if restart_required else "")
            + (f" {len(errors)} error(s)." if errors else "")
        ),
    }
