"""Gemini adapter."""
from typing import AsyncIterator, Any
import google.generativeai as genai
from .base import LLMAdapter, ModelInfo


class GeminiAdapter(LLMAdapter):
    """Gemini LLM adapter."""
    
    def _validate_config(self) -> None:
        if 'api_key' not in self.config:
            raise ValueError("Gemini api_key is required")
        genai.configure(api_key=self.config['api_key'])
        self.model_name = self.config.get('default_model', self.config.get('model', 'gemini-3.6-flash'))
        self.model = genai.GenerativeModel(self.model_name)
    
    def _convert_messages(self, messages: list[dict[str, str]]) -> tuple[str, list[dict[str, Any]]]:
        """Convert OpenAI-style messages to Gemini format.
        
        Returns (system_instruction, chat_history).
        System messages are extracted as system_instruction.
        Consecutive same-role messages are merged.
        """
        system_parts = []
        chat_messages = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                system_parts.append(content)
                continue
            
            gemini_role = "model" if role == "assistant" else "user"
            
            # Merge consecutive same-role messages
            if chat_messages and chat_messages[-1]["role"] == gemini_role:
                chat_messages[-1]["parts"].append(content)
            else:
                chat_messages.append({"role": gemini_role, "parts": [content]})
        
        system_instruction = "\n\n".join(system_parts) if system_parts else ""
        return system_instruction, chat_messages
    
    async def complete(self, messages: list[dict[str, str]], **kwargs) -> str:
        try:
            system_instruction, chat_messages = self._convert_messages(messages)
            
            # Use system_instruction if available
            if system_instruction:
                model = genai.GenerativeModel(
                    self.model_name,
                    system_instruction=system_instruction,
                )
            else:
                model = self.model
            
            response = await model.generate_content_async(chat_messages)
            return response.text
        except Exception as e:
            raise RuntimeError(f"Gemini error: {e}")
    
    async def stream(self, messages: list[dict[str, str]], **kwargs) -> AsyncIterator[str]:
        try:
            system_instruction, chat_messages = self._convert_messages(messages)
            
            if system_instruction:
                model = genai.GenerativeModel(
                    self.model_name,
                    system_instruction=system_instruction,
                )
            else:
                model = self.model
            
            response = await model.generate_content_async(chat_messages, stream=True)
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            raise RuntimeError(f"Gemini streaming error: {e}")
            
    def get_model_info(self) -> ModelInfo:
        return ModelInfo(
            provider="gemini",
            model_name=self.model_name,
            max_tokens=8192,
            supports_streaming=True,
            supports_function_calling=True
        )
