"""
LLM Vision Client with Provider Switch (Gemini free tier & Ollama local vision).
Provides a unified interface: analyze(image_bytes, prompt, json_schema) -> validated JSON.
Handles rate limits with exponential backoff and automatically falls back to OCR.
Never logs API keys or credentials.
"""

import asyncio
import base64
import json
import os
import re
import tempfile
from typing import Any, Dict, Optional, Type, Union
from pathlib import Path
from pydantic import BaseModel

import httpx
from app.core.logging.logger import get_logger

logger = get_logger(__name__)


def _mask_key(key: Optional[str]) -> str:
    """Safely masks an API key for logs without leaking secrets."""
    if not key:
        return "[NOT_SET]"
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"


class VisionClientError(Exception):
    """Base exception for VisionClient failures."""
    pass


class VisionRateLimitError(VisionClientError):
    """Raised when the vision provider rate limit is exceeded after retries."""
    pass


class VisionClient:
    """
    Unified multimodal vision client supporting:
      1. Google Gemini (free tier via Google AI Studio / GEMINI_API_KEY)
      2. Ollama (local vision models: Qwen-VL, Llama-vision, LLaVA)
      3. OCR fallback (Tesseract / PIL) when vision calls fail or keys are missing.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
    ) -> None:
        self.provider = (provider or os.getenv("VISION_PROVIDER", "gemini")).lower().strip()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        if self.provider == "ollama":
            self.model = model or os.getenv("OLLAMA_VISION_MODEL", os.getenv("VISION_MODEL", "qwen2.5-vl"))
            self.base_url = (base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        else:
            self.provider = "gemini"
            self.model = model or os.getenv("GEMINI_VISION_MODEL", os.getenv("VISION_MODEL", "gemini-2.5-flash"))
            self.base_url = "https://generativelanguage.googleapis.com"

        logger.info(
            f"Initialized VisionClient with provider='{self.provider}', "
            f"model='{self.model}', key={_mask_key(self.api_key)}"
        )

    async def analyze(
        self,
        image_bytes: bytes,
        prompt: str,
        json_schema: Optional[Union[Dict[str, Any], Type[BaseModel]]] = None,
    ) -> Dict[str, Any]:
        """
        Analyzes an image with the configured vision model and returns validated JSON.
        If the vision call fails (rate limit, missing key, network error),
        gracefully falls back to local OCR extraction.
        """
        try:
            if self.provider == "ollama":
                raw_json = await self._call_ollama(image_bytes, prompt, json_schema)
            else:
                raw_json = await self._call_gemini(image_bytes, prompt, json_schema)

            validated = self._validate_json(raw_json, json_schema)
            return validated

        except Exception as e:
            logger.warning(
                f"Vision provider '{self.provider}' call failed: {type(e).__name__} - {e}. "
                "Falling back to OCR text extraction."
            )
            return await self._fallback_ocr(image_bytes, prompt, json_schema, error=str(e))

    def analyze_sync(
        self,
        image_bytes: bytes,
        prompt: str,
        json_schema: Optional[Union[Dict[str, Any], Type[BaseModel]]] = None,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for analyze()."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, self.analyze(image_bytes, prompt, json_schema)).result()
            else:
                return loop.run_until_complete(self.analyze(image_bytes, prompt, json_schema))
        except RuntimeError:
            return asyncio.run(self.analyze(image_bytes, prompt, json_schema))

    async def _call_gemini(
        self,
        image_bytes: bytes,
        prompt: str,
        json_schema: Optional[Union[Dict[str, Any], Type[BaseModel]]],
    ) -> Dict[str, Any]:
        """Calls Google Gemini Vision API with exponential backoff on 429."""
        if not self.api_key:
            raise VisionClientError("GEMINI_API_KEY is not configured.")

        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        system_instruction = (
            "You are a multimodal vision analyst. Respond strictly in valid JSON format. "
            "Do not include Markdown code blocks (```json ... ```) or conversational commentary outside the JSON."
        )

        schema_prompt = ""
        if json_schema:
            schema_repr = (
                json.dumps(json_schema.model_json_schema(), indent=2)
                if isinstance(json_schema, type) and issubclass(json_schema, BaseModel)
                else json.dumps(json_schema, indent=2)
            )
            schema_prompt = f"\nOutput MUST strictly conform to this JSON schema:\n{schema_repr}\n"

        full_prompt = f"{system_instruction}\n{schema_prompt}\nTASK: {prompt}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": full_prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": b64_image,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {"response_mime_type": "application/json"},
        }

        last_err = None
        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=45.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 429:
                        delay = self.backoff_factor ** attempt
                        logger.warning(
                            f"Gemini Vision rate limited (429). Backing off for {delay:.1f}s (Attempt {attempt}/{self.max_retries})."
                        )
                        await asyncio.sleep(delay)
                        continue

                    resp.raise_for_status()
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise VisionClientError("Gemini returned empty candidates.")
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if not parts:
                        raise VisionClientError("Gemini returned no parts in response.")
                    raw_text = parts[0].get("text", "")
                    return self._parse_json_string(raw_text)

            except httpx.HTTPStatusError as e:
                last_err = e
                if e.response.status_code == 429 and attempt < self.max_retries:
                    delay = self.backoff_factor ** attempt
                    await asyncio.sleep(delay)
                    continue
                raise VisionClientError(f"Gemini Vision HTTP error {e.response.status_code}: {e}") from e
            except Exception as e:
                last_err = e
                if attempt < self.max_retries:
                    await asyncio.sleep(self.backoff_factor)
                    continue
                raise VisionClientError(f"Gemini Vision call failed: {e}") from e

        raise VisionRateLimitError(
            f"Gemini rate limit exceeded after {self.max_retries} attempts: {last_err}"
        )

    async def _call_ollama(
        self,
        image_bytes: bytes,
        prompt: str,
        json_schema: Optional[Union[Dict[str, Any], Type[BaseModel]]],
    ) -> Dict[str, Any]:
        """Calls local Ollama Vision API."""
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        url = f"{self.base_url}/api/generate"

        schema_prompt = ""
        if json_schema:
            schema_repr = (
                json.dumps(json_schema.model_json_schema(), indent=2)
                if isinstance(json_schema, type) and issubclass(json_schema, BaseModel)
                else json.dumps(json_schema, indent=2)
            )
            schema_prompt = f"\nRespond ONLY with valid JSON conforming to this schema:\n{schema_repr}\n"

        full_prompt = f"{prompt}\n{schema_prompt}"

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "images": [b64_image],
            "format": "json",
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data.get("response", "")
            return self._parse_json_string(raw_text)

    def _parse_json_string(self, text: str) -> Dict[str, Any]:
        """Extracts and parses JSON object from model output text."""
        cleaned = text.strip()
        # Remove potential markdown fences
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Fallback regex search for { ... }
            match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            raise VisionClientError(f"Failed to parse JSON from vision response: {cleaned[:200]}")

    def _validate_json(
        self,
        data: Dict[str, Any],
        schema: Optional[Union[Dict[str, Any], Type[BaseModel]]],
    ) -> Dict[str, Any]:
        """Validates dictionary against Pydantic schema or returns data."""
        if not schema:
            return data

        if isinstance(schema, type) and issubclass(schema, BaseModel):
            validated_obj = schema.model_validate(data)
            return validated_obj.model_dump()

        return data

    async def _fallback_ocr(
        self,
        image_bytes: bytes,
        prompt: str,
        json_schema: Optional[Union[Dict[str, Any], Type[BaseModel]]],
        error: str = "",
    ) -> Dict[str, Any]:
        """Runs local OCR extraction as fallback when vision models fail."""
        extracted_text = ""
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                f.write(image_bytes)
                temp_file = Path(f.name)

            # 1. Try pytesseract directly if installed
            try:
                import pytesseract
                from PIL import Image
                with Image.open(temp_file) as img:
                    extracted_text = pytesseract.image_to_string(img).strip()
            except Exception as ocr_ex:
                logger.debug(f"PyTesseract direct run note: {ocr_ex}")

            # 2. Try OCREngine if available
            if not extracted_text:
                try:
                    from app.tools.ocr.engine import OCREngine
                    from shared.contracts.ocr import OCRRequest
                    engine = OCREngine()
                    res = await engine.extract_text(OCRRequest(image_path=str(temp_file)))
                    extracted_text = res.raw_text or res.text or ""
                except Exception as ocr_ex:
                    logger.debug(f"OCREngine fallback note: {ocr_ex}")

        finally:
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass

        # Build fallback output compatible with schema
        ocr_summary = extracted_text[:1000] if extracted_text else "No text detected via OCR fallback."
        fallback_dict: Dict[str, Any] = {
            "thought": f"Vision model unavailable ({error}). OCR fallback extracted page text: {ocr_summary[:200]}",
            "action": "wait",
            "summary": f"OCR text extracted: {ocr_summary}",
            "ocr_text": ocr_summary,
            "fallback": True,
            "provider": "ocr_fallback",
        }

        # If schema is Pydantic, construct model with sensible defaults
        if isinstance(json_schema, type) and issubclass(json_schema, BaseModel):
            try:
                # Attempt to validate directly with fallback_dict
                return json_schema.model_validate(fallback_dict).model_dump()
            except Exception:
                # Construct minimal valid instance
                constructed: Dict[str, Any] = {}
                for field_name, field_info in json_schema.model_fields.items():
                    if field_name in fallback_dict:
                        constructed[field_name] = fallback_dict[field_name]
                    elif field_info.is_required():
                        # Fill safe placeholders
                        if field_info.annotation in (str, Optional[str]):
                            constructed[field_name] = ocr_summary[:100]
                        elif field_info.annotation in (int, float, Optional[int], Optional[float]):
                            constructed[field_name] = 0
                        elif field_info.annotation in (bool, Optional[bool]):
                            constructed[field_name] = False
                        elif getattr(field_info.annotation, "__name__", "") == "ActionType":
                            constructed[field_name] = "wait"
                        else:
                            constructed[field_name] = None
                    else:
                        constructed[field_name] = field_info.default

                try:
                    return json_schema.model_validate(constructed).model_dump()
                except Exception as ex:
                    logger.warning(f"Could not coerce OCR fallback into schema {json_schema}: {ex}")

        return fallback_dict


# Factory / Singleton helper
_global_vision_client: Optional[VisionClient] = None


def get_vision_client() -> VisionClient:
    """Returns singleton VisionClient instance based on current environment."""
    global _global_vision_client
    if _global_vision_client is None:
        _global_vision_client = VisionClient()
    return _global_vision_client
