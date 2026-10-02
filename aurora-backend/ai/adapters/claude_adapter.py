"""Claude adapter."""
from typing import AsyncIterator, Any
import anthropic
from .base import LLMAdapter, ModelInfo

class ClaudeAdapter(LLMAdapter):
    """Claude LLM adapter."""
    
    def _validate_config(self) -> None:
        if 'api_key' not in self.config:
            raise ValueError("Anthropic api_key is required")
        self.client = anthropic.AsyncAnthropic(api_key=self.config['api_key'])
        self.model_name = self.config.get('model', 'claude-3-5-sonnet-20240620')
    
    def _extract_system(self, messages: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
        system_msg = ""
        filtered_msgs = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg += msg["content"] + "\n"
            else:
                filtered_msgs.append(msg)
        return system_msg.strip(), filtered_msgs
        
    async def complete(self, messages: list[dict[str, str]], **kwargs) -> str:
        try:
            system, chat_messages = self._extract_system(messages)
            response = await self.client.messages.create(
                model=self.model_name,
                messages=chat_messages,
                system=system if system else None,
                max_tokens=kwargs.get('max_tokens', 4096),
                temperature=kwargs.get('temperature', 0.7),
            )
            return response.content[0].text
        except Exception as e:
            raise RuntimeError(f"Claude error: {e}")
    
    async def stream(self, messages: list[dict[str, str]], **kwargs) -> AsyncIterator[str]:
        try:
            system, chat_messages = self._extract_system(messages)
            stream = await self.client.messages.create(
                model=self.model_name,
                messages=chat_messages,
                system=system if system else None,
                max_tokens=kwargs.get('max_tokens', 4096),
                temperature=kwargs.get('temperature', 0.7),
                stream=True
            )
            async for event in stream:
                if event.type == "content_block_delta":
                    yield event.delta.text
        except Exception as e:
            raise RuntimeError(f"Claude streaming error: {e}")
            
    def get_model_info(self) -> ModelInfo:
        return ModelInfo(
            provider="anthropic",
            model_name=self.model_name,
            max_tokens=8192,
            supports_streaming=True,
            supports_function_calling=True
        )
