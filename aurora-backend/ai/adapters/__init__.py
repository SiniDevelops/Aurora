"""AI adapters initialization."""
from .base import LLMAdapter, EmbeddingAdapter
from .openai_adapter import OpenAIAdapter, OpenAIEmbeddingAdapter
from .gemini_adapter import GeminiAdapter
from .claude_adapter import ClaudeAdapter
from .ollama_adapter import OllamaAdapter, OllamaEmbeddingAdapter

__all__ = [
    'LLMAdapter', 'EmbeddingAdapter',
    'OpenAIAdapter', 'OpenAIEmbeddingAdapter',
    'GeminiAdapter', 'ClaudeAdapter',
    'OllamaAdapter', 'OllamaEmbeddingAdapter',
]
