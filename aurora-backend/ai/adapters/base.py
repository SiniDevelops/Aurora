"""Base classes for AI adapters."""
from abc import ABC, abstractmethod
from typing import AsyncIterator, Any
from pydantic import BaseModel

class ModelInfo(BaseModel):
    """Model information."""
    provider: str
    model_name: str
    max_tokens: int
    supports_streaming: bool = True
    supports_function_calling: bool = False

class LLMAdapter(ABC):
    """Abstract base for all LLM providers. Swap providers by changing aurora.yaml."""
    
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self._validate_config()
    
    @abstractmethod
    def _validate_config(self) -> None:
        """Validate provider-specific config."""
        pass
    
    @abstractmethod
    async def complete(self, messages: list[dict[str, str]], **kwargs) -> str:
        """Send messages and get a complete response."""
        pass
    
    @abstractmethod
    async def stream(self, messages: list[dict[str, str]], **kwargs) -> AsyncIterator[str]:
        """Stream response tokens."""
        pass
    
    @abstractmethod
    def get_model_info(self) -> ModelInfo:
        """Return model metadata."""
        pass

class EmbeddingAdapter(ABC):
    """Abstract base for embedding providers."""
    
    def __init__(self, config: dict[str, Any]):
        self.config = config
    
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        pass
    
    @abstractmethod
    async def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        pass
