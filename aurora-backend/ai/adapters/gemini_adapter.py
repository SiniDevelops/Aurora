"""Gemini adapter.

Notes on transport (important on Windows):
- The default gRPC transport of ``google.generativeai`` silently retries
  429/503 responses inside the SDK, so ``generate_content_async`` can appear
  to hang for minutes. The async REST path of the same SDK is broken
  ("GenerateContentResponse can't be used in 'await' expression").
- We therefore use the REST transport with *synchronous* calls executed in a
  worker thread, with an explicit HTTP timeout, SDK retries disabled, and an
  outer ``asyncio.wait_for`` as a hard stop. Our own backoff handles 429s.
"""
import asyncio
import logging
from typing import AsyncIterator, Any
import google.generativeai as genai
from .base import LLMAdapter, ModelInfo

logger = logging.getLogger("aurora.gemini")

_STREAM_END = object()


class GeminiTimeoutError(RuntimeError):
    """Raised when a Gemini request exceeds the configured timeout."""


class GeminiAdapter(LLMAdapter):
    """Gemini LLM adapter with exponential backoff retry for rate limits."""

    DEFAULT_MAX_RETRIES = 3
    DEFAULT_BACKOFF_DELAYS = [2, 4, 8]
    DEFAULT_TIMEOUT = 60  # seconds per request

    def _validate_config(self) -> None:
        if 'api_key' not in self.config:
            raise ValueError("Gemini api_key is required")
        genai.configure(api_key=self.config['api_key'], transport="rest")
        self.model_name = self._clean_name(
            self.config.get('default_model', self.config.get('model', 'gemini-3.6-flash'))
        )
        self.fallback_models = [self._clean_name(m) for m in self.config.get('fallback_models', []) or []]
        self.timeout = float(self.config.get('timeout', self.DEFAULT_TIMEOUT))
        self.temperature = self.config.get('temperature')
        self.max_tokens = self.config.get('max_tokens')
        self.model = genai.GenerativeModel(self.model_name)

    @staticmethod
    def _clean_name(name: str) -> str:
        # list_models() returns "models/gemini-..."; GenerativeModel wants "gemini-..."
        return name[len('models/'):] if name.startswith('models/') else name

    # ------------------------------------------------------------------ errors
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

        code = getattr(error, "code", None)
        if code == 429 or code == "429":
            return True
        status_code = getattr(error, "status_code", None)
        if status_code == 429 or status_code == "429":
            return True

        error_str = str(error).lower()
        class_name = type(error).__name__.lower()
        indicators = ["429", "resource_exhausted", "resourceexhausted", "rate limit", "ratelimit", "quota exceeded"]
        return any(ind in error_str or ind in class_name for ind in indicators)

    def _is_unavailable_error(self, error: Exception) -> bool:
        """503 / overloaded / timeout -> worth trying a fallback model."""
        if isinstance(error, GeminiTimeoutError):
            return True
        try:
            from google.api_core import exceptions as google_exceptions
            if isinstance(error, (google_exceptions.ServiceUnavailable, google_exceptions.DeadlineExceeded)):
                return True
        except ImportError:
            pass
        text = f"{type(error).__name__} {error}".lower()
        return any(s in text for s in ("503", "unavailable", "overloaded", "readtimeout", "timed out"))

    # ---------------------------------------------------------------- helpers
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

            if chat_messages and chat_messages[-1]["role"] == gemini_role:
                chat_messages[-1]["parts"].append(content)
            else:
                chat_messages.append({"role": gemini_role, "parts": [content]})

        system_instruction = "\n\n".join(system_parts) if system_parts else ""
        return system_instruction, chat_messages

    def _get_model(self, model_name: str, system_instruction: str):
        if system_instruction or model_name != self.model_name:
            return genai.GenerativeModel(model_name, system_instruction=system_instruction or None)
        return self.model

    def _generation_config(self, kwargs: dict) -> dict | None:
        cfg = {}
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        if temperature is not None:
            cfg["temperature"] = temperature
        if max_tokens is not None:
            cfg["max_output_tokens"] = max_tokens
        return cfg or None

    async def _run_blocking(self, fn, *args, **kwargs):
        """Run a blocking SDK call in a thread with a hard timeout."""
        try:
            return await asyncio.wait_for(asyncio.to_thread(fn, *args, **kwargs), timeout=self.timeout + 5)
        except asyncio.TimeoutError:
            raise GeminiTimeoutError(f"Gemini request timed out after {self.timeout:.0f}s")

    def _request_kwargs(self, kwargs: dict, stream: bool = False) -> dict:
        req = {"request_options": {"timeout": self.timeout, "retry": None}}
        gen_cfg = self._generation_config(kwargs)
        if gen_cfg:
            req["generation_config"] = gen_cfg
        if stream:
            req["stream"] = True
        return req

    @staticmethod
    def _chunk_text(chunk) -> str:
        try:
            return chunk.text or ""
        except (ValueError, AttributeError):
            # Chunks without text parts (e.g. safety/finish metadata) raise on .text
            return ""

    # ------------------------------------------------------------- completion
    async def complete(self, messages: list[dict[str, str]], **kwargs) -> str:
        system_instruction, chat_messages = self._convert_messages(messages)
        models_to_try = [self.model_name] + [m for m in self.fallback_models if m != self.model_name]
        last_error: Exception | None = None

        for idx, model_name in enumerate(models_to_try):
            try:
                return await self._complete_with_retry(model_name, system_instruction, chat_messages, kwargs)
            except Exception as e:
                last_error = e
                if self._is_unavailable_error(e) and idx < len(models_to_try) - 1:
                    logger.warning(f"Gemini model '{model_name}' unavailable ({e}); falling back to '{models_to_try[idx + 1]}'")
                    continue
                raise
        raise last_error  # pragma: no cover

    async def _complete_with_retry(self, model_name, system_instruction, chat_messages, kwargs) -> str:
        max_retries = kwargs.get("max_retries", self.DEFAULT_MAX_RETRIES)
        backoff_delays = kwargs.get("backoff_delays", self.DEFAULT_BACKOFF_DELAYS)
        model = self._get_model(model_name, system_instruction)

        for attempt in range(max_retries + 1):
            try:
                response = await self._run_blocking(
                    model.generate_content, chat_messages, **self._request_kwargs(kwargs)
                )
                return response.text
            except GeminiTimeoutError:
                raise
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
                    logger.error(f"Gemini API rate limit (429) retries exhausted after {max_retries} attempts: {e}")
                    raise e
                if self._is_unavailable_error(e):
                    raise
                raise RuntimeError(f"Gemini error: {e}")

    # -------------------------------------------------------------- streaming
    async def stream(self, messages: list[dict[str, str]], **kwargs) -> AsyncIterator[str]:
        system_instruction, chat_messages = self._convert_messages(messages)
        models_to_try = [self.model_name] + [m for m in self.fallback_models if m != self.model_name]

        for idx, model_name in enumerate(models_to_try):
            yielded_any = False
            try:
                async for text in self._stream_with_retry(model_name, system_instruction, chat_messages, kwargs):
                    yielded_any = True
                    yield text
                return
            except Exception as e:
                if not yielded_any and self._is_unavailable_error(e) and idx < len(models_to_try) - 1:
                    logger.warning(f"Gemini model '{model_name}' unavailable ({e}); falling back to '{models_to_try[idx + 1]}'")
                    continue
                raise

    async def _stream_with_retry(self, model_name, system_instruction, chat_messages, kwargs) -> AsyncIterator[str]:
        max_retries = kwargs.get("max_retries", self.DEFAULT_MAX_RETRIES)
        backoff_delays = kwargs.get("backoff_delays", self.DEFAULT_BACKOFF_DELAYS)
        model = self._get_model(model_name, system_instruction)

        for attempt in range(max_retries + 1):
            yielded_any = False
            try:
                response = await self._run_blocking(
                    model.generate_content, chat_messages, **self._request_kwargs(kwargs, stream=True)
                )
                iterator = iter(response)
                while True:
                    chunk = await self._run_blocking(next, iterator, _STREAM_END)
                    if chunk is _STREAM_END:
                        break
                    text = self._chunk_text(chunk)
                    if text:
                        yielded_any = True
                        yield text
                return
            except GeminiTimeoutError:
                raise
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
                    logger.error(f"Gemini streaming rate limit (429) retries exhausted after {max_retries} attempts: {e}")
                    raise e
                if self._is_rate_limit_error(e) or self._is_unavailable_error(e):
                    raise
                raise RuntimeError(f"Gemini streaming error: {e}")

    def get_model_info(self) -> ModelInfo:
        return ModelInfo(
            provider="gemini",
            model_name=self.model_name,
            max_tokens=8192,
            supports_streaming=True,
            supports_function_calling=True
        )
