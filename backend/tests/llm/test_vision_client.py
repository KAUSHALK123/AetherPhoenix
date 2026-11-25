"""
Unit tests for VisionClient (Stage 0).
Tests:
1. Provider switch (Gemini vs Ollama).
2. Rate limit handling with exponential backoff.
3. Schema validation against Pydantic models.
4. Graceful OCR fallback when vision API calls fail or keys are missing.
5. Key masking security.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest
from pydantic import BaseModel, Field

from app.llm.vision_client import (
    VisionClient,
    VisionClientError,
    VisionRateLimitError,
    _mask_key,
)


class MockActionSchema(BaseModel):
    thought: str = Field(..., description="Reasoning")
    action: str = Field(..., description="Action type")
    summary: str = Field("", description="Optional summary")


def test_mask_key_security():
    assert _mask_key(None) == "[NOT_SET]"
    assert _mask_key("") == "[NOT_SET]"
    assert _mask_key("short") == "***"
    masked = _mask_key("AIzaSyD-1234567890abcdef")
    assert masked == "AIza...cdef"
    assert "1234567890" not in masked


def test_provider_switch_initialization():
    # 1. Default Gemini
    with patch.dict(os.environ, {"VISION_PROVIDER": "gemini", "GEMINI_API_KEY": "test-key-123"}):
        client = VisionClient()
        assert client.provider == "gemini"
        assert client.model == "gemini-2.5-flash"
        assert client.api_key == "test-key-123"

    # 2. Ollama provider
    with patch.dict(os.environ, {"VISION_PROVIDER": "ollama", "OLLAMA_VISION_MODEL": "qwen2.5-vl", "OLLAMA_HOST": "http://127.0.0.1:11434"}):
        client = VisionClient()
        assert client.provider == "ollama"
        assert client.model == "qwen2.5-vl"
        assert client.base_url == "http://127.0.0.1:11434"


@pytest.mark.asyncio
async def test_gemini_vision_successful_call_with_schema():
    client = VisionClient(provider="gemini", api_key="valid-test-key")

    mock_gemini_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": '{"thought": "Detected solar panel layout", "action": "click", "summary": "Clicked panel"}'
                        }
                    ]
                }
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_gemini_response
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await client.analyze(
            image_bytes=b"fake-png-bytes",
            prompt="Analyze this slide",
            json_schema=MockActionSchema,
        )

        assert result["thought"] == "Detected solar panel layout"
        assert result["action"] == "click"
        assert result["summary"] == "Clicked panel"


@pytest.mark.asyncio
async def test_gemini_rate_limit_backoff_and_retry():
    client = VisionClient(provider="gemini", api_key="valid-key", max_retries=2, backoff_factor=1.1)

    mock_429_resp = MagicMock()
    mock_429_resp.status_code = 429

    mock_200_resp = MagicMock()
    mock_200_resp.status_code = 200
    mock_200_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": '{"thought": "Recovered after backoff", "action": "wait", "summary": "ok"}'}]}}]
    }
    mock_200_resp.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        # First call returns 429, second call succeeds
        mock_post.side_effect = [mock_429_resp, mock_200_resp]
        result = await client.analyze(
            image_bytes=b"fake-bytes",
            prompt="Analyze screen",
            json_schema=MockActionSchema,
        )

        assert mock_post.call_count == 2
        assert result["thought"] == "Recovered after backoff"


@pytest.mark.asyncio
async def test_fallback_to_ocr_when_vision_call_fails():
    client = VisionClient(provider="gemini", api_key="failing-key", max_retries=1)

    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Network unreachable")):
        # Mock OCR fallback text extraction
        with patch.object(client, "_fallback_ocr", new_callable=AsyncMock) as mock_fallback:
            mock_fallback.return_value = {
                "thought": "OCR fallback: Detected heading text",
                "action": "wait",
                "summary": "Extracted via OCR",
                "fallback": True,
            }

            result = await client.analyze(
                image_bytes=b"sample-bytes",
                prompt="Check slide content",
                json_schema=MockActionSchema,
            )

            assert result["fallback"] is True
            assert "OCR fallback" in result["thought"]


@pytest.mark.asyncio
async def test_ollama_vision_call():
    client = VisionClient(provider="ollama", model="qwen2.5-vl", base_url="http://127.0.0.1:11434")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "response": '{"thought": "Local Ollama recognized UI buttons", "action": "click", "summary": "Found button"}'
    }
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await client.analyze(
            image_bytes=b"fake-ollama-bytes",
            prompt="Locate primary button",
            json_schema=MockActionSchema,
        )

        assert result["thought"] == "Local Ollama recognized UI buttons"
        assert result["action"] == "click"
