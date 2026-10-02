"""
Embeddings Manager — Handles text embedding with provider adapters and caching.

Gracefully degrades if no embedding provider is configured — semantic search
will be unavailable but all other features work.
"""

from typing import Any
import hashlib
import logging

from .adapters.base import EmbeddingAdapter

logger = logging.getLogger("aurora.embeddings")


class NoOpEmbeddingAdapter(EmbeddingAdapter):
    """Fallback adapter that returns zero vectors when no provider is available."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 384 for _ in texts]

    async def embed_single(self, text: str) -> list[float]:
        return [0.0] * 384


class EmbeddingManager:
    """
    Manager for generating text embeddings with caching.
    
    Falls back to NoOpEmbeddingAdapter if the configured provider
    cannot be initialized (e.g., missing API key).
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.active_provider = config.get("active_provider", config.get("provider", ""))
        self.providers_config = config.get("providers", {})
        self.cache: dict[str, list[float]] = {}
        self.adapter = self._load_adapter()

    def _load_adapter(self) -> EmbeddingAdapter:
        """Load the embedding adapter, falling back to NoOp on failure."""
        provider_info = self.providers_config.get(self.active_provider, {})
        adapter_config = provider_info.get("config", provider_info)

        try:
            if self.active_provider == "openai":
                from .adapters.openai_adapter import OpenAIEmbeddingAdapter
                return OpenAIEmbeddingAdapter(adapter_config)
            elif self.active_provider == "ollama":
                from .adapters.ollama_adapter import OllamaEmbeddingAdapter
                return OllamaEmbeddingAdapter(adapter_config)
            else:
                logger.warning(
                    f"No embedding adapter for provider '{self.active_provider}'. "
                    "Semantic search will be unavailable."
                )
                return NoOpEmbeddingAdapter()
        except Exception as e:
            logger.warning(
                f"Failed to initialize embedding adapter ({self.active_provider}): {e}. "
                "Falling back to NoOp — semantic search will be unavailable."
            )
            return NoOpEmbeddingAdapter()

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts with caching."""
        results: list[list[float]] = []
        texts_to_embed: list[str] = []
        indices_to_embed: list[tuple[int, str]] = []

        for i, text in enumerate(texts):
            text_hash = self._hash_text(text)
            if text_hash in self.cache:
                results.append(self.cache[text_hash])
            else:
                results.append([])  # placeholder
                texts_to_embed.append(text)
                indices_to_embed.append((i, text_hash))

        if texts_to_embed:
            new_embeddings = await self.adapter.embed(texts_to_embed)
            for (idx, text_hash), embedding in zip(indices_to_embed, new_embeddings):
                self.cache[text_hash] = embedding
                results[idx] = embedding

        return results

    async def embed_single(self, text: str) -> list[float]:
        """Embed a single text with caching."""
        text_hash = self._hash_text(text)
        if text_hash in self.cache:
            return self.cache[text_hash]

        embedding = await self.adapter.embed_single(text)
        self.cache[text_hash] = embedding
        return embedding
