"""
LLM Provider — pluggable interface for LLM-backed agent reasoning.

Agents can optionally use an LLM provider to generate proposals
via natural language reasoning instead of deterministic rules.

This module provides the abstract interface and a stub implementation.
Real providers (OpenAI, Google GenAI, LiteLLM) can be added as needed.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """
    Abstract interface for LLM-backed reasoning.

    Agents can inject an LLMProvider to enhance their core_execute()
    method with natural language generation capabilities.
    """

    @abstractmethod
    def generate(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """
        Generate a text response from the LLM.

        Args:
            prompt: The instruction/prompt for the LLM
            context: Optional context dict to include in the prompt
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens in the response

        Returns:
            The generated text response
        """
        ...

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate a structured JSON response matching the given schema.

        This is preferred for agent core_execute() since the output
        must conform to the Shared Vocabulary.

        Args:
            prompt: The instruction/prompt for the LLM
            schema: JSON schema the output must conform to
            context: Optional context dict

        Returns:
            A dict matching the provided schema
        """
        ...


class StubLLMProvider(LLMProvider):
    """
    Stub LLM provider for testing and development.

    Returns placeholder responses without making any API calls.
    """

    def generate(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        return (
            f"[StubLLM] This is a placeholder response. "
            f"Prompt length: {len(prompt)} chars. "
            f"Context keys: {list(context.keys()) if context else 'none'}"
        )

    def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        # Return a minimal valid response based on schema
        result: dict[str, Any] = {}
        properties = schema.get("properties", {})
        for key, spec in properties.items():
            field_type = spec.get("type", "string")
            if field_type == "string":
                result[key] = f"[stub-{key}]"
            elif field_type == "number" or field_type == "float":
                result[key] = 0.5
            elif field_type == "integer":
                result[key] = 0
            elif field_type == "boolean":
                result[key] = True
            elif field_type == "array":
                result[key] = []
            elif field_type == "object":
                result[key] = {}
        return result
