"""
Shared Gemini client for the matching module.

Configuration via environment variables:
    GEMINI_API_KEY  — required
    GEMINI_MODEL    — model ID to use, default "gemini-3.5-flash-lite"
"""

from __future__ import annotations

import os
from typing import Any, TypeVar

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv()

MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

_TIMEOUT_MS = 60_000

T = TypeVar("T", bound=BaseModel)


def get_client() -> genai.Client:
    """Return a Gemini client with the standard 60 s timeout.

    Raises:
        ValueError: If GEMINI_API_KEY is not set.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set")
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=_TIMEOUT_MS),
    )


def generate_json(system: str, text: str, schema: type[T]) -> T:
    """Call Gemini and return a validated Pydantic object.

    Args:
        system: System instruction for the model.
        text:   User content to process.
        schema: Pydantic model class used as the response schema.

    Returns:
        Validated instance of *schema*.

    Raises:
        ValueError: If GEMINI_API_KEY is not set.
        google.genai.errors.APIError: On API errors.
    """
    client = get_client()
    response = client.models.generate_content(
        model=MODEL,
        contents=text,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0,
        ),
    )
    return schema.model_validate_json(response.text)
