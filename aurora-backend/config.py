"""
Aurora Backend — Configuration Manager

Loads aurora.yaml, interpolates environment variables, and provides
typed access to all configuration values.
"""

import os
import re
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


# Load .env file from project root
_PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


class AuroraConfig:
    """
    Loads and manages Aurora configuration from aurora.yaml.
    
    Supports ${ENV_VAR} syntax for environment variable interpolation.
    Falls back to empty string if env var is not set.
    """

    _ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")

    def __init__(self, config_path: str | None = None):
        if config_path is None:
            config_path = str(_PROJECT_ROOT / "aurora.yaml")
        
        self._config_path = Path(config_path)
        self._raw: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load and parse the YAML configuration file."""
        if not self._config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self._config_path}"
            )
        
        with open(self._config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        
        if not isinstance(raw, dict):
            raise ValueError("aurora.yaml must contain a YAML mapping at the top level")
        
        self._raw = self._interpolate_env(raw)

    def _interpolate_env(self, obj: Any) -> Any:
        """Recursively interpolate ${ENV_VAR} patterns in config values."""
        if isinstance(obj, str):
            return self._ENV_VAR_PATTERN.sub(self._env_replacer, obj)
        elif isinstance(obj, dict):
            return {k: self._interpolate_env(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._interpolate_env(item) for item in obj]
        return obj

    @staticmethod
    def _env_replacer(match: re.Match) -> str:
        """Replace ${VAR} with environment variable value."""
        var_name = match.group(1)
        return os.environ.get(var_name, "")

    def reload(self) -> None:
        """Reload configuration from disk."""
        self._load()

    # ─── Accessors ───────────────────────────────────────

    @property
    def raw(self) -> dict[str, Any]:
        """Raw configuration dictionary."""
        return self._raw

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a nested config value using dot-notation.
        
        Example: config.get("llm.active_provider") -> "openai"
        """
        keys = key_path.split(".")
        value = self._raw
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    # ─── App ─────────────────────────────────────────────

    @property
    def app_name(self) -> str:
        return self.get("app.name", "Aurora")

    @property
    def app_version(self) -> str:
        return self.get("app.version", "1.0.0")

    @property
    def debug(self) -> bool:
        return self.get("app.debug", False)

    @property
    def host(self) -> str:
        return self.get("app.host", "0.0.0.0")

    @property
    def port(self) -> int:
        return self.get("app.port", 8000)

    # ─── Vault ───────────────────────────────────────────

    @property
    def vault_path(self) -> str:
        path = self.get("vault.path", "")
        return str(Path(path).expanduser().resolve())

    @property
    def vault_excluded_folders(self) -> list[str]:
        return self.get("vault.excluded_folders", [".obsidian", ".trash", ".git"])

    @property
    def vault_supported_extensions(self) -> list[str]:
        return self.get("vault.supported_extensions", [".md"])

    @property
    def vault_watch_changes(self) -> bool:
        return self.get("vault.watch_changes", True)

    @property
    def vault_index_on_startup(self) -> bool:
        return self.get("vault.index_on_startup", True)

    # ─── LLM ────────────────────────────────────────────

    @property
    def llm_active_provider(self) -> str:
        return self.get("llm.active_provider", "openai")

    @property
    def llm_providers(self) -> dict[str, Any]:
        return self.get("llm.providers", {})

    @property
    def llm_active_config(self) -> dict[str, Any]:
        provider = self.llm_active_provider
        providers = self.llm_providers
        if provider not in providers:
            raise ValueError(
                f"Active LLM provider '{provider}' not found in config. "
                f"Available: {list(providers.keys())}"
            )
        return providers[provider].get("config", {})

    @property
    def embedding_active_provider(self) -> str:
        return self.get("llm.embedding.active_provider", "openai")

    @property
    def embedding_providers(self) -> dict[str, Any]:
        return self.get("llm.embedding.providers", {})

    @property
    def embedding_active_config(self) -> dict[str, Any]:
        provider = self.embedding_active_provider
        providers = self.embedding_providers
        if provider not in providers:
            raise ValueError(
                f"Active embedding provider '{provider}' not found in config. "
                f"Available: {list(providers.keys())}"
            )
        return providers[provider].get("config", {})

    # ─── Privacy ─────────────────────────────────────────

    @property
    def privacy_config(self) -> dict[str, Any]:
        return self.get("privacy", {})

    @property
    def privacy_enabled(self) -> bool:
        return self.get("privacy.enabled", True)

    @property
    def pii_detection_enabled(self) -> bool:
        return self.get("privacy.pii_detection", True)

    @property
    def privacy_content_rules(self) -> list[dict]:
        return self.get("privacy.content_rules", [])

    # ─── Skills ──────────────────────────────────────────

    @property
    def skills_config(self) -> dict[str, Any]:
        return self.get("skills", {})

    @property
    def skills_builtin(self) -> dict[str, Any]:
        return self.get("skills.builtin", {})

    @property
    def skills_router_config(self) -> dict[str, Any]:
        return self.get("skills.router", {})

    @property
    def skills_custom_path(self) -> str:
        return self.get("skills.custom_skills_path", "./skills/custom")

    @property
    def skills_auto_discover(self) -> bool:
        return self.get("skills.auto_discover", True)

    # ─── Database ────────────────────────────────────────

    @property
    def sqlite_path(self) -> str:
        return self.get("database.sqlite.path", "./data/aurora.db")

    @property
    def chroma_path(self) -> str:
        return self.get("database.vector_store.config.path", "./data/chroma")

    @property
    def chroma_collection(self) -> str:
        return self.get("database.vector_store.config.collection_name", "aurora_vault")

    # ─── Logging ─────────────────────────────────────────

    @property
    def log_level(self) -> str:
        return self.get("logging.level", "INFO")

    @property
    def log_file(self) -> str:
        return self.get("logging.file", "./logs/aurora.log")

    # ─── Security ────────────────────────────────────────

    @property
    def auth_enabled(self) -> bool:
        return self.get("security.auth_enabled", False)

    @property
    def pin_lock(self) -> str | None:
        pin = self.get("security.pin_lock", "")
        return pin if pin else None

    @property
    def session_timeout_minutes(self) -> int:
        return self.get("security.session_timeout_minutes", 60)


# Global config instance — initialized on first import
_config: AuroraConfig | None = None


def get_config(config_path: str | None = None) -> AuroraConfig:
    """Get or create the global config instance."""
    global _config
    if _config is None:
        _config = AuroraConfig(config_path)
    return _config


def reload_config() -> AuroraConfig:
    """Force reload the configuration from disk."""
    global _config
    _config = None
    return get_config()
