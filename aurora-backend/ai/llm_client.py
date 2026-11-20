"""LLM Client for active provider management."""
from typing import AsyncIterator, Any, Dict
from .adapters.base import LLMAdapter, ModelInfo
from .adapters.openai_adapter import OpenAIAdapter
from .adapters.gemini_adapter import GeminiAdapter
from .adapters.claude_adapter import ClaudeAdapter
from .adapters.ollama_adapter import OllamaAdapter

class LLMClient:
    """Provider-agnostic LLM client."""
    
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.active_provider = config.get('active_provider', 'openai')
        self.providers_config = config.get('providers', {})
        self.adapter = self._load_adapter(self.active_provider, self.providers_config.get(self.active_provider, {}))
        
        fallback_provider = config.get('fallback_provider')
        self.fallback_adapter = None
        if fallback_provider and fallback_provider in self.providers_config:
            self.fallback_adapter = self._load_adapter(fallback_provider, self.providers_config[fallback_provider])

    def _load_adapter(self, provider_name: str, provider_config: dict[str, Any]) -> LLMAdapter:
        # YAML structure is: providers.gemini.config.api_key
        # Extract the inner 'config' dict that has the actual settings
        adapter_config = provider_config.get('config', provider_config)
        if provider_name == 'openai':
            return OpenAIAdapter(adapter_config)
        elif provider_name == 'gemini':
            return GeminiAdapter(adapter_config)
        elif provider_name in ('anthropic', 'claude'):
            return ClaudeAdapter(adapter_config)
        elif provider_name == 'ollama':
            return OllamaAdapter(adapter_config)
        else:
            raise ValueError(f"Unknown provider: {provider_name}")

    async def complete(self, messages: list[dict[str, str]], **kwargs) -> str:
        try:
            return await self.adapter.complete(messages, **kwargs)
        except Exception as e:
            if self.fallback_adapter:
                return await self.fallback_adapter.complete(messages, **kwargs)
            raise e

    async def stream(self, messages: list[dict[str, str]], **kwargs) -> AsyncIterator[str]:
        try:
            async for chunk in self.adapter.stream(messages, **kwargs):
                yield chunk
        except Exception as e:
            if self.fallback_adapter:
                async for chunk in self.fallback_adapter.stream(messages, **kwargs):
                    yield chunk
            else:
                raise e

    def get_active_provider(self) -> str:
        return self.active_provider

    def switch_provider(self, provider_name: str, provider_config: dict[str, Any]) -> None:
        """Hot-swap the active LLM adapter at runtime."""
        new_adapter = self._load_adapter(provider_name, provider_config)
        self.providers_config[provider_name] = provider_config
        self.active_provider = provider_name
        self.adapter = new_adapter

    def get_model_info(self) -> ModelInfo:
        return self.adapter.get_model_info()
