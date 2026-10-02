"""OpenAI adapters."""
from typing import AsyncIterator, Any
import openai
from .base import LLMAdapter, EmbeddingAdapter, ModelInfo

class OpenAIAdapter(LLMAdapter):
    """OpenAI LLM adapter."""
    
    def _validate_config(self) -> None:
        if 'api_key' not in self.config:
            raise ValueError("OpenAI api_key is required")
        self.client = openai.AsyncOpenAI(api_key=self.config['api_key'])
        self.model_name = self.config.get('model', 'gpt-4o')
    
    async def complete(self, messages: list[dict[str, str]], **kwargs) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=kwargs.get('temperature', 0.7),
                max_tokens=kwargs.get('max_tokens'),
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"OpenAI error: {e}")
    
    async def stream(self, messages: list[dict[str, str]], **kwargs) -> AsyncIterator[str]:
        try:
            stream = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=kwargs.get('temperature', 0.7),
                max_tokens=kwargs.get('max_tokens'),
                stream=True
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise RuntimeError(f"OpenAI streaming error: {e}")
            
    def get_model_info(self) -> ModelInfo:
        return ModelInfo(
            provider="openai",
            model_name=self.model_name,
            max_tokens=8192,
            supports_streaming=True,
            supports_function_calling=True
        )

class OpenAIEmbeddingAdapter(EmbeddingAdapter):
    """OpenAI embedding adapter."""
    
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        if 'api_key' not in self.config:
            raise ValueError("OpenAI api_key is required")
        self.client = openai.AsyncOpenAI(api_key=self.config['api_key'])
        self.model_name = self.config.get('model', 'text-embedding-3-small')
        
    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self.client.embeddings.create(
            input=texts,
            model=self.model_name
        )
        return [data.embedding for data in response.data]
        
    async def embed_single(self, text: str) -> list[float]:
        result = await self.embed([text])
        return result[0]
