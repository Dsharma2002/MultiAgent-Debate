"""
Shared Vocabulary — Strict data schemas for the Common-Ground Layer.

All agents must parse and emit data matching these exact keys.
No synonyms are permitted (e.g., do not use 'cost' for 'budget_allocation').
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

import yaml
from pydantic import BaseModel, Field, model_validator


class VocabularyFieldType(str, Enum):
    """Supported field types in the vocabulary schema."""

    UUID = "uuid"
    FLOAT = "float"
    INTEGER = "integer"
    STRING = "string"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"


class VocabularyFieldSpec(BaseModel):
    """Specification for a single vocabulary field."""

    type: VocabularyFieldType
    required: bool = False
    min: float | None = None
    max: float | None = None
    unit: str | None = None
    description: str | None = None


class VocabularyRegistry:
    """
    Registry of all approved vocabulary keys.

    Any data dict containing unrecognized keys is REJECTED.
    This prevents synonym drift (e.g., using 'cost' instead of 'budget_allocation').
    """

    def __init__(self) -> None:
        self._fields: dict[str, VocabularyFieldSpec] = {}

    @classmethod
    def from_yaml(cls, path: str) -> VocabularyRegistry:
        """Load vocabulary definitions from a YAML file."""
        with open(path, "r") as f:
            raw = yaml.safe_load(f)

        registry = cls()
        vocab_section = raw.get("vocabulary", {})
        for key, spec_data in vocab_section.items():
            spec = VocabularyFieldSpec(**spec_data)
            registry.register(key, spec)
        return registry

    def register(self, key: str, spec: VocabularyFieldSpec) -> None:
        """Register a vocabulary field."""
        self._fields[key] = spec

    def get_spec(self, key: str) -> VocabularyFieldSpec | None:
        """Get the spec for a given key, or None if not registered."""
        return self._fields.get(key)

    @property
    def approved_keys(self) -> set[str]:
        """Return the set of all approved vocabulary keys."""
        return set(self._fields.keys())

    @property
    def required_keys(self) -> set[str]:
        """Return the set of required vocabulary keys."""
        return {k for k, v in self._fields.items() if v.required}

    def validate_data(self, data: dict[str, Any]) -> list[str]:
        """
        Validate a data dict against the vocabulary.

        Returns a list of error strings. Empty list means valid.
        """
        errors: list[str] = []

        # Check for unapproved keys (synonym prevention)
        unapproved = set(data.keys()) - self.approved_keys
        if unapproved:
            errors.append(
                f"Unapproved vocabulary keys detected: {sorted(unapproved)}. "
                f"Approved keys are: {sorted(self.approved_keys)}"
            )

        # Check for missing required keys
        missing = self.required_keys - set(data.keys())
        if missing:
            errors.append(f"Missing required vocabulary keys: {sorted(missing)}")

        # Type and range validation for present keys
        for key, value in data.items():
            spec = self._fields.get(key)
            if spec is None:
                continue  # Already caught above

            # Type checks
            type_errors = self._validate_type(key, value, spec)
            errors.extend(type_errors)

            # Range checks (for numeric types)
            if spec.min is not None and isinstance(value, (int, float)):
                if value < spec.min:
                    errors.append(
                        f"Field '{key}' value {value} is below minimum {spec.min}"
                    )
            if spec.max is not None and isinstance(value, (int, float)):
                if value > spec.max:
                    errors.append(
                        f"Field '{key}' value {value} exceeds maximum {spec.max}"
                    )

        return errors

    def _validate_type(
        self, key: str, value: Any, spec: VocabularyFieldSpec
    ) -> list[str]:
        """Validate the type of a single field value."""
        errors: list[str] = []
        expected = spec.type

        type_map: dict[VocabularyFieldType, type | tuple[type, ...]] = {
            VocabularyFieldType.UUID: (str, UUID),
            VocabularyFieldType.FLOAT: (int, float),
            VocabularyFieldType.INTEGER: int,
            VocabularyFieldType.STRING: str,
            VocabularyFieldType.BOOLEAN: bool,
            VocabularyFieldType.LIST: list,
            VocabularyFieldType.DICT: dict,
        }

        expected_type = type_map.get(expected)
        if expected_type and not isinstance(value, expected_type):
            errors.append(
                f"Field '{key}' expected type {expected.value}, "
                f"got {type(value).__name__}"
            )

        # Special: for UUID strings, validate format
        if expected == VocabularyFieldType.UUID and isinstance(value, str):
            try:
                UUID(value)
            except ValueError:
                errors.append(f"Field '{key}' is not a valid UUID string: {value}")

        return errors

    def __repr__(self) -> str:
        return f"VocabularyRegistry(fields={sorted(self._fields.keys())})"


class Proposal(BaseModel):
    """
    A proposal data model matching the Shared Vocabulary.

    This is a convenience model for structured proposal creation.
    Agents may also work with raw dicts validated through VocabularyRegistry.
    """

    proposal_id: str = Field(description="Unique proposal identifier (UUID4 string)")
    tech_feasibility_score: float = Field(
        ge=0.0, le=1.0, description="Technical feasibility score (0.0 to 1.0)"
    )
    budget_allocation: int = Field(
        ge=0, description="Budget allocation in USD"
    )
    description: str = Field(default="", description="Proposal description")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Extensible metadata"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_proposal_id_is_uuid(cls, data: Any) -> Any:
        """Ensure proposal_id is a valid UUID string."""
        if isinstance(data, dict):
            pid = data.get("proposal_id")
            if pid is not None and isinstance(pid, str):
                try:
                    UUID(pid)
                except ValueError:
                    raise ValueError(f"proposal_id must be a valid UUID, got: {pid}")
        return data

    def to_vocabulary_dict(self) -> dict[str, Any]:
        """Convert to a flat dict suitable for vocabulary validation."""
        result: dict[str, Any] = {
            "proposal_id": self.proposal_id,
            "tech_feasibility_score": self.tech_feasibility_score,
            "budget_allocation": self.budget_allocation,
        }
        if self.description:
            result["description"] = self.description
        if self.metadata:
            result["metadata"] = self.metadata
        return result
