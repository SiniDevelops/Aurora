import importlib
import logging
from typing import Dict, List, Optional, Any
from .base_skill import BaseSkill
from data.models import SkillMetadata

class SkillRegistry:
    """Registry for managing and discovering skills."""
    
    def __init__(self, config: dict):
        # config is already the 'skills' section from aurora.yaml
        self.config = config
        self._skills: Dict[str, BaseSkill] = {}
        
    async def initialize(self, vault_manager: Any, llm_client: Any, logger: logging.Logger) -> None:
        """Load and initialize built-in skills based on YAML config."""
        self.vault_manager = vault_manager
        self.llm_client = llm_client
        self.logger = logger
        
        builtin_config = self.config.get('builtin', {})
        for skill_name, skill_config in builtin_config.items():
            if skill_config.get('enabled', False):
                try:
                    module = importlib.import_module('skills.builtin')
                    class_name = "".join(word.capitalize() for word in skill_name.split('_')) + "Skill"
                    skill_class = getattr(module, class_name)
                    skill_instance = skill_class(vault_manager, llm_client, logger)
                    self.register(skill_instance)
                except (ImportError, AttributeError) as e:
                    logger.error(f"Failed to load skill {skill_name}: {e}")
                    
    def register(self, skill: BaseSkill) -> None:
        """Register a skill by its metadata.id."""
        self._skills[skill.metadata.id] = skill
        
    def unregister(self, skill_id: str) -> None:
        """Unregister a skill by its ID."""
        if skill_id in self._skills:
            del self._skills[skill_id]
            
    async def load_and_register(self, skill_name: str, vault_manager: Any = None, llm_client: Any = None, logger: logging.Logger = None) -> None:
        """Dynamically load and register a single builtin skill by its ID."""
        try:
            module = importlib.import_module('skills.builtin')
            class_name = "".join(word.capitalize() for word in skill_name.split('_')) + "Skill"
            skill_class = getattr(module, class_name)
            # Create a dummy or real instance, it requires these dependencies
            # We assume they are stored in the registry from initialize
            v_mgr = vault_manager or self.vault_manager
            llm_cli = llm_client or self.llm_client
            log = logger or self.logger
            skill_instance = skill_class(v_mgr, llm_cli, log)
            self.register(skill_instance)
        except (ImportError, AttributeError) as e:
            if self.logger:
                self.logger.error(f"Failed to load skill {skill_name}: {e}")

    def get_skill(self, skill_id: str) -> Optional[BaseSkill]:
        """Retrieve a registered skill by its ID."""
        return self._skills.get(skill_id)
        
    def get_enabled_skills(self) -> List[BaseSkill]:
        """Return all skills marked enabled in config."""
        return list(self._skills.values())
        
    def get_skill_descriptions(self) -> List[Dict[str, Any]]:
        """Return skill descriptions for LLM routing."""
        return [
            {
                "id": skill.metadata.id,
                "name": skill.metadata.name,
                "description": skill.metadata.description,
                "triggers": skill.metadata.triggers,
                "examples": skill.metadata.examples
            }
            for skill in self._skills.values()
        ]
        
    def list_skills(self) -> List[SkillMetadata]:
        """List metadata for all registered skills."""
        return [skill.metadata for skill in self._skills.values()]
