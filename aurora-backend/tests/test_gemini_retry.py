"""
Unit tests for Gemini adapter retry logic on 429 rate limit errors.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from google.api_core import exceptions as google_exceptions

from ai.adapters.gemini_adapter import GeminiAdapter


class TestGeminiAdapterRetry:
    """Test suite for GeminiAdapter rate limit retries."""

    @pytest.fixture
    def adapter(self):
        with patch("google.generativeai.configure"):
            with patch("google.generativeai.GenerativeModel"):
                adapter = GeminiAdapter({"api_key": "fake-key", "default_model": "gemini-1.5-flash"})
                return adapter

    @pytest.mark.asyncio
    async def test_complete_succeeds_first_attempt(self, adapter):
        """Standard complete without errors."""
        mock_response = MagicMock()
        mock_response.text = "Hello world"
        
        adapter.model = MagicMock()
        adapter.model.generate_content_async = AsyncMock(return_value=mock_response)

        messages = [{"role": "user", "content": "Hi"}]
        result = await adapter.complete(messages)

        assert result == "Hello world"
        assert adapter.model.generate_content_async.call_count == 1

    @pytest.mark.asyncio
    async def test_complete_retries_on_429_and_succeeds(self, adapter):
        """Fails twice with 429 ResourceExhausted, succeeds on 3rd attempt."""
        err_429 = google_exceptions.ResourceExhausted("429 Resource has been exhausted")
        mock_response = MagicMock()
        mock_response.text = "Recovered response"

        adapter.model = MagicMock()
        adapter.model.generate_content_async = AsyncMock(
            side_effect=[err_429, err_429, mock_response]
        )

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
             patch("ai.adapters.gemini_adapter.logger.warning") as mock_log_warn:
            messages = [{"role": "user", "content": "Test"}]
            result = await adapter.complete(messages)

            assert result == "Recovered response"
            assert adapter.model.generate_content_async.call_count == 3
            # Check backoff delays: first retry 2s, second retry 4s
            assert mock_sleep.call_count == 2
            mock_sleep.assert_any_call(2)
            mock_sleep.assert_any_call(4)
            # Check retry logging
            assert mock_log_warn.call_count == 2
            assert "Retry attempt 1/3" in mock_log_warn.call_args_list[0][0][0]
            assert "Retry attempt 2/3" in mock_log_warn.call_args_list[1][0][0]

    @pytest.mark.asyncio
    async def test_complete_exhausts_retries_and_raises_original_error(self, adapter):
        """Fails 4 times with 429 (initial + 3 retries), raises original ResourceExhausted error."""
        err_429 = google_exceptions.ResourceExhausted("429 Resource has been exhausted")

        adapter.model = MagicMock()
        adapter.model.generate_content_async = AsyncMock(side_effect=err_429)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
             patch("ai.adapters.gemini_adapter.logger.warning") as mock_log_warn, \
             patch("ai.adapters.gemini_adapter.logger.error") as mock_log_err:
            messages = [{"role": "user", "content": "Test"}]
            
            with pytest.raises(google_exceptions.ResourceExhausted) as exc_info:
                await adapter.complete(messages)

            # Original error is preserved
            assert exc_info.value is err_429
            # Exactly 4 calls: 1 initial + 3 retries
            assert adapter.model.generate_content_async.call_count == 4
            # Backoff delays were 2s, 4s, 8s
            assert mock_sleep.call_count == 3
            mock_sleep.assert_any_call(2)
            mock_sleep.assert_any_call(4)
            mock_sleep.assert_any_call(8)
            # Logged all 3 retry attempts and 1 exhausted error
            assert mock_log_warn.call_count == 3
            assert mock_log_err.call_count == 1

    @pytest.mark.asyncio
    async def test_complete_non_429_error_raises_without_retry(self, adapter):
        """Non-429 error (e.g. ValueError) is not retried and raises RuntimeError."""
        non_rate_err = ValueError("Invalid prompt format")

        adapter.model = MagicMock()
        adapter.model.generate_content_async = AsyncMock(side_effect=non_rate_err)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            messages = [{"role": "user", "content": "Test"}]
            with pytest.raises(RuntimeError) as exc_info:
                await adapter.complete(messages)

            assert "Gemini error: Invalid prompt format" in str(exc_info.value)
            # Should not retry
            assert adapter.model.generate_content_async.call_count == 1
            assert mock_sleep.call_count == 0

    @pytest.mark.asyncio
    async def test_stream_retries_on_429_and_succeeds(self, adapter):
        """Streaming retries on 429 and streams chunks successfully."""
        err_429 = google_exceptions.ResourceExhausted("429 Resource has been exhausted")
        
        async def fake_stream():
            for word in ["Hello", " ", "world"]:
                chunk = MagicMock()
                chunk.text = word
                yield chunk

        adapter.model = MagicMock()
        adapter.model.generate_content_async = AsyncMock(
            side_effect=[err_429, fake_stream()]
        )

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
             patch("ai.adapters.gemini_adapter.logger.warning") as mock_log_warn:
            messages = [{"role": "user", "content": "Test"}]
            chunks = []
            async for chunk in adapter.stream(messages):
                chunks.append(chunk)

            assert "".join(chunks) == "Hello world"
            assert adapter.model.generate_content_async.call_count == 2
            assert mock_sleep.call_count == 1
            mock_sleep.assert_called_once_with(2)
            assert mock_log_warn.call_count == 1

    @pytest.mark.asyncio
    async def test_stream_exhausts_retries_and_raises_original_error(self, adapter):
        """Streaming exhausts all 3 retries and raises original ResourceExhausted error."""
        err_429 = google_exceptions.ResourceExhausted("429 Resource has been exhausted")

        adapter.model = MagicMock()
        adapter.model.generate_content_async = AsyncMock(side_effect=err_429)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
             patch("ai.adapters.gemini_adapter.logger.error") as mock_log_err:
            messages = [{"role": "user", "content": "Test"}]
            
            with pytest.raises(google_exceptions.ResourceExhausted) as exc_info:
                async for _ in adapter.stream(messages):
                    pass

            assert exc_info.value is err_429
            assert adapter.model.generate_content_async.call_count == 4
            assert mock_sleep.call_count == 3
            mock_sleep.assert_any_call(2)
            mock_sleep.assert_any_call(4)
            mock_sleep.assert_any_call(8)
            assert mock_log_err.call_count == 1
