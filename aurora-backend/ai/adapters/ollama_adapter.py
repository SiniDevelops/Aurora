"""Ollama adapters."""
from typing import AsyncIterator, Any
import httpx
import json
from .base import LLMAdapter, EmbeddingAdapter, ModelInfo

class OllamaAdapter(LLMAdapter):
    """Ollama local LLM adapter."""
    
    def _validate_config(self) -> None:
        self.base_url = self.config.get('base_url', 'http://localhost:11434')
        self.model_name = self.config.get('model', 'llama3')
    
    async def complete(self, messages: list[dict[str, str]], **kwargs) -> str:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": kwargs.get('temperature', 0.7)
                        }
                    },
                    timeout=kwargs.get('timeout', 60.0)
                )
                response.raise_for_status()
                return response.json()['message']['content']
            except httpx.RequestError as e:
                raise RuntimeError(f"Ollama connection error (is it running?): {e}")
    
    async def stream(self, messages: list[dict[str, str]], **kwargs) -> AsyncIterator[str]:
        async with httpx.AsyncClient() as client:
            try:
                async with client.stream(
                    "POST", 
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "stream": True,
                        "options": {
                            "temperature": kwargs.get('temperature', 0.7)
                        }
                    }
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            data = json.loads(line)
                            if 'message' in data and 'content' in data['message']:
                                yield data['message']['content']
            except httpx.RequestError as e:
                raise RuntimeError(f"Ollama streaming connection error: {e}")
            
    def get_model_info(self) -> ModelInfo:
        return ModelInfo(
            provider="ollama",
            model_name=self.model_name,
            max_tokens=4096,
            supports_streaming=True,
            supports_function_calling=False
        )

class OllamaEmbeddingAdapter(EmbeddingAdapter):
    """Ollama embedding adapter."""
    
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.base_url = self.config.get('base_url', 'http://localhost:11434')
        self.model_name = self.config.get('model', 'nomic-embed-text')
        
    async def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = []
        async with httpx.AsyncClient() as client:
            try:
                for text in texts:
                    response = await client.post(
                        f"{self.base_url}/api/embeddings",
                        json={
                            "model": self.model_name,
                            "prompt": text
                        }
                    )
                    response.raise_for_status()
                    embeddings.append(response.json()['embedding'])
                return embeddings
            except httpx.RequestError as e:
                raise RuntimeError(f"Ollama embeddings connection error: {e}")
        
    async def embed_single(self, text: str) -> list[float]:
        result = await self.embed([text])
        return result[0]
