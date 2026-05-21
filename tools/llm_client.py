"""
LLM Client for LedgerMind.

Thin wrapper around the Anthropic Claude SDK. Provides a single interface
that all agents use, with built-in retry, timeout handling, and an optional
mock mode for testing without API costs.
"""

import json
import os
import time
from typing import Any

from anthropic import Anthropic, APIError, APITimeoutError


class LLMClient:
    """Centralized LLM client for all agents."""

    def __init__(self, mock_mode: bool | None = None):
        self.mock_mode = mock_mode if mock_mode is not None else os.getenv("MOCK_MODE", "false").lower() == "true"
        self.model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")

        if not self.mock_mode:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY not set. Either set the environment variable "
                    "or run in mock mode by setting MOCK_MODE=true."
                )
            self.client = Anthropic(api_key=api_key)
        else:
            self.client = None

    def complete(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 1500,
        temperature: float = 0.2,
        max_retries: int = 2,
    ) -> dict[str, Any]:
        """
        Send a message to the LLM and return the response.

        Returns:
            Dict with keys: content (str), usage (dict), latency_ms (float),
            model (str), mock (bool).
        """
        if self.mock_mode:
            return self._mock_complete(system_prompt, user_message)

        start = time.time()
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )
                latency_ms = (time.time() - start) * 1000
                return {
                    "content": response.content[0].text,
                    "usage": {
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                    },
                    "latency_ms": round(latency_ms, 1),
                    "model": self.model,
                    "mock": False,
                }
            except (APIError, APITimeoutError) as e:
                last_error = e
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                else:
                    raise

        raise RuntimeError(f"LLM call failed after {max_retries} retries: {last_error}")

    def complete_json(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 1500,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """
        Call the LLM and parse the response as JSON. The agent prompt is
        responsible for instructing the model to return valid JSON.

        Returns the same shape as `complete()` but with `content` replaced by
        the parsed JSON object under key `parsed`.
        """
        response = self.complete(system_prompt, user_message, max_tokens, temperature)
        raw = response["content"].strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            parsed = {
                "parse_error": True,
                "error_message": str(e),
                "raw_content": response["content"],
            }

        response["parsed"] = parsed
        return response

    def _mock_complete(self, system_prompt: str, user_message: str) -> dict[str, Any]:
        """Return a deterministic mock response for testing."""
        return {
            "content": json.dumps({
                "verdict": "MOCK_RESPONSE",
                "confidence": 0.5,
                "reasoning": f"Mock mode is enabled. System prompt was {len(system_prompt)} chars, user message was {len(user_message)} chars.",
                "abstain": False,
            }),
            "usage": {"input_tokens": 100, "output_tokens": 50},
            "latency_ms": 1.0,
            "model": "mock",
            "mock": True,
        }
