"""Gemini adapter."""
import asyncio
import logging
from typing import AsyncIterator, Any
import google.generativeai as genai
from .base import LLMAdapter, ModelInfo

logger = logging.getLogger("aurora.gemini")


class GeminiAdapter(LLMAdapter):
    """Gemini LLM adapter with exponential backoff retry for rate limits."""
    
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_BACKOFF_DELAYS = [2, 4, 8]
    
    def _validate_config(self) -> None:
        if 'api_key' not in self.config:
            raise ValueError("Gemini api_key is required")
        genai.configure(api_key=self.config['api_key'])
        self.model_name = self.config.get('default_model', self.config.get('model', 'gemini-3.6-flash'))
        self.model = genai.GenerativeModel(self.model_name)
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if an exception is a 429 rate limit error."""
        try:
            from google.api_core import exceptions as google_exceptions
            if isinstance(error, google_exceptions.ResourceExhausted):
                return True
            if hasattr(google_exceptions, "TooManyRequests") and isinstance(error, google_exceptions.TooManyRequests):
                return True
        except ImportError:
            pass

        # Check for status code 429
        code = getattr(error, "code", None)
        if code == 429 or code == "429":
            return True
        status_code = getattr(error, "status_code", None)
        if status_code == 429 or status_code == "429":
            return True

        # Check exception string / class name
        error_str = str(error).lower()
        class_name = type(error).__name__.lower()
        indicators = ["429", "resource_exhausted", "resourceexhausted", "rate limit", "ratelimit", "quota exceeded"]
        if any(ind in error_str or ind in class_name for ind in indicators):
            return True

        return False

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
        max_retries = kwargs.get("max_retries", self.DEFAULT_MAX_RETRIES)
        backoff_delays = kwargs.get("backoff_delays", self.DEFAULT_BACKOFF_DELAYS)
        
        for attempt in range(max_retries + 1):
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
                if self._is_rate_limit_error(e):
                    if attempt < max_retries:
                        delay = backoff_delays[attempt]
                        logger.warning(
                            f"Gemini API rate limit (429) hit. Retry attempt {attempt + 1}/{max_retries} "
                            f"after {delay}s backoff. Error: {e}"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(
                            f"Gemini API rate limit (429) retries exhausted after {max_retries} attempts: {e}"
                        )
                        raise e
                raise RuntimeError(f"Gemini error: {e}")
    
    async def stream(self, messages: list[dict[str, str]], **kwargs) -> AsyncIterator[str]:
        max_retries = kwargs.get("max_retries", self.DEFAULT_MAX_RETRIES)
        backoff_delays = kwargs.get("backoff_delays", self.DEFAULT_BACKOFF_DELAYS)
        
        for attempt in range(max_retries + 1):
            yielded_any = False
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
                        yielded_any = True
                        yield chunk.text
                return
            except Exception as e:
                if not yielded_any and self._is_rate_limit_error(e):
                    if attempt < max_retries:
                        delay = backoff_delays[attempt]
                        logger.warning(
                            f"Gemini streaming rate limit (429) encountered. Retrying in {delay}s "
                            f"(attempt {attempt + 1}/{max_retries}). Error: {e}"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(
                            f"Gemini streaming rate limit (429) retries exhausted after {max_retries} attempts: {e}"
                        )
                        raise e
                if self._is_rate_limit_error(e):
                    raise e
                raise RuntimeError(f"Gemini streaming error: {e}")
            
    def get_model_info(self) -> ModelInfo:
        return ModelInfo(
            provider="gemini",
            model_name=self.model_name,
            max_tokens=8192,
            supports_streaming=True,
            supports_function_calling=True
        )
