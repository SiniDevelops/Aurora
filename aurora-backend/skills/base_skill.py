import logging
from abc import ABC, abstractmethod
from typing import Any, Tuple

from data.models import SkillMetadata, SkillInput, SkillOutput, SkillAction

class BaseSkill(ABC):
    """Abstract base class for all skills."""
    
    metadata: SkillMetadata
    
    def __init__(self, vault_manager: Any, llm_client: Any, logger: logging.Logger):
        self.vault_manager = vault_manager
        self.llm_client = llm_client
        self.logger = logger
        
    @abstractmethod
    async def execute(self, input: SkillInput) -> SkillOutput:
        """Execute the skill with the given input."""
        pass
        
    @abstractmethod
    def can_handle(self, user_input: str) -> float:
        """Return a confidence score (0.0-1.0) for handling the input."""
        pass
        
    async def validate_input(self, input: SkillInput) -> Tuple[bool, str]:
        """Validate the input before execution."""
        return True, ""
        
    async def pre_execute(self, input: SkillInput) -> None:
        """Hook called before execution."""
        self.logger.info(f"Executing skill {self.metadata.id} with input: {input}")
        
    async def post_execute(self, output: SkillOutput) -> SkillOutput:
        """Hook called after execution."""
        self.logger.info(f"Finished skill {self.metadata.id} execution.")
        return output
        
    def get_system_prompt(self) -> str:
        """Return the system prompt for the skill based on its metadata."""
        return self.metadata.description
