"""
Constraint Registry — defines and loads shared hard constraints.

Constraints are immutable business rules that every evidence entry
must satisfy before being committed to the Truth Ledger.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import yaml

from mad.ledger.base import LedgerBackend
from mad.schemas.evidence import EvidenceEntry


# Type alias for constraint rule functions.
# A rule receives (entry, ledger) and returns (passed: bool, reason: str | None).
ConstraintRuleFn = Callable[[EvidenceEntry, LedgerBackend], tuple[bool, str | None]]


@dataclass
class Constraint:
    """A single hard constraint / guardrail."""

    constraint_id: str
    description: str
    rule_fn: ConstraintRuleFn
    applies_to_agents: list[str] = field(default_factory=lambda: ["*"])

    def applies_to(self, agent_id: str) -> bool:
        """Check if this constraint applies to the given agent."""
        return "*" in self.applies_to_agents or agent_id in self.applies_to_agents


@dataclass
class ConstraintResult:
    """Result of evaluating all applicable constraints on an entry."""

    passed: bool
    violations: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        if self.passed:
            return "PASSED: All constraints satisfied"
        return f"FAILED: {len(self.violations)} violation(s) — {'; '.join(self.violations)}"


class ConstraintRegistry:
    """
    Registry that holds all shared constraints.

    Constraints can be registered programmatically or loaded from YAML config
    (YAML maps constraint IDs to metadata; rule functions must be registered
    in code since YAML cannot serialize callables).
    """

    def __init__(self) -> None:
        self._constraints: dict[str, Constraint] = {}

    def register(self, constraint: Constraint) -> None:
        """Register a constraint."""
        self._constraints[constraint.constraint_id] = constraint

    def get(self, constraint_id: str) -> Constraint | None:
        """Get a constraint by ID."""
        return self._constraints.get(constraint_id)

    def get_all(self) -> list[Constraint]:
        """Return all registered constraints."""
        return list(self._constraints.values())

    def get_for_agent(self, agent_id: str) -> list[Constraint]:
        """Return all constraints applicable to a given agent."""
        return [c for c in self._constraints.values() if c.applies_to(agent_id)]

    def load_metadata_from_yaml(self, path: str) -> None:
        """
        Load constraint metadata (ID, description, applies_to) from YAML.

        Rule functions must be registered separately via register_rule().
        This separation is intentional — YAML defines WHAT the constraints are,
        Python code defines HOW they are enforced.
        """
        with open(path, "r") as f:
            raw = yaml.safe_load(f)

        for constraint_data in raw.get("constraints", []):
            cid = constraint_data["constraint_id"]
            existing = self._constraints.get(cid)
            if existing:
                # Update metadata but keep existing rule_fn
                existing.description = constraint_data.get(
                    "description", existing.description
                )
                existing.applies_to_agents = constraint_data.get(
                    "applies_to_agents", existing.applies_to_agents
                )
            else:
                # Create placeholder — rule_fn must be set later
                self._constraints[cid] = Constraint(
                    constraint_id=cid,
                    description=constraint_data.get("description", ""),
                    rule_fn=_placeholder_rule,
                    applies_to_agents=constraint_data.get(
                        "applies_to_agents", ["*"]
                    ),
                )

    def register_rule(self, constraint_id: str, rule_fn: ConstraintRuleFn) -> None:
        """Attach a rule function to an existing constraint."""
        constraint = self._constraints.get(constraint_id)
        if constraint is None:
            raise KeyError(
                f"Constraint '{constraint_id}' not found. "
                f"Register it first or load from YAML."
            )
        constraint.rule_fn = rule_fn

    def __len__(self) -> int:
        return len(self._constraints)

    def __repr__(self) -> str:
        return f"ConstraintRegistry(constraints={list(self._constraints.keys())})"


def _placeholder_rule(
    entry: EvidenceEntry, ledger: LedgerBackend
) -> tuple[bool, str | None]:
    """Placeholder rule that always fails — must be replaced with actual logic."""
    return False, (
        "Constraint rule not implemented. "
        "Register a rule_fn via ConstraintRegistry.register_rule()."
    )


# ─── Built-in Constraint Rules (matching the blueprint) ───────────────────────


def budget_limit_rule(
    entry: EvidenceEntry,
    ledger: LedgerBackend,
    max_budget: int = 5000,
) -> tuple[bool, str | None]:
    """
    Constraint_01: Total budget_allocation must never exceed the limit.

    Checks current ledger total + this entry's budget against the max.
    """
    new_budget = entry.content.get("budget_allocation", 0)
    if not isinstance(new_budget, int):
        return False, f"budget_allocation must be an integer, got {type(new_budget).__name__}"

    current_total = ledger.get_total_budget()
    projected_total = current_total + new_budget

    if projected_total > max_budget:
        return False, (
            f"Budget violation: current total ${current_total} + "
            f"new ${new_budget} = ${projected_total} exceeds limit ${max_budget}"
        )
    return True, None


def security_boundary_rule(
    entry: EvidenceEntry,
    ledger: LedgerBackend,
    restricted_agents: list[str] | None = None,
) -> tuple[bool, str | None]:
    """
    Constraint_02: High-security data inputs cannot be handled by restricted agents.

    By default, agent 'qa_engineer' (UX) is restricted from security-sensitive data.
    """
    if restricted_agents is None:
        restricted_agents = ["qa_engineer"]

    is_security_sensitive = entry.content.get("security_classification") in (
        "high",
        "critical",
        "confidential",
    )

    if is_security_sensitive and entry.author_agent_id in restricted_agents:
        return False, (
            f"Security boundary violation: agent '{entry.author_agent_id}' "
            f"is not authorized to handle security-classified data "
            f"(classification: {entry.content.get('security_classification')})"
        )
    return True, None


def peer_validation_rule(
    entry: EvidenceEntry,
    ledger: LedgerBackend,
    min_validations: int = 2,
) -> tuple[bool, str | None]:
    """
    Constraint_03: No proposal can move to output without minimum peer validations.

    This constraint is enforced at the pipeline level (VerificationGate)
    rather than at the individual entry level. It checks the
    'peer_validations' count in the entry content.
    """
    validations = entry.content.get("peer_validations", 0)
    if isinstance(validations, int) and validations >= min_validations:
        return True, None

    # If peer_validations field is not present, this is a draft entry
    # The pipeline will add validations during the audit phase
    if "peer_validations" not in entry.content:
        return True, None  # Deferred to pipeline audit phase

    return False, (
        f"Peer validation requirement not met: {validations}/{min_validations} "
        f"validations received"
    )


def create_default_registry() -> ConstraintRegistry:
    """
    Create a ConstraintRegistry pre-loaded with the blueprint's 3 constraints.

    This is the recommended way to bootstrap the system.
    """
    registry = ConstraintRegistry()

    registry.register(
        Constraint(
            constraint_id="constraint_01",
            description="Total budget allocation must never exceed $5,000",
            rule_fn=lambda e, l: budget_limit_rule(e, l, max_budget=5000),
            applies_to_agents=["*"],
        )
    )

    registry.register(
        Constraint(
            constraint_id="constraint_02",
            description="High-security data inputs cannot be handled by Agent 3 (UX/QA)",
            rule_fn=lambda e, l: security_boundary_rule(
                e, l, restricted_agents=["qa_engineer"]
            ),
            applies_to_agents=["*"],
        )
    )

    registry.register(
        Constraint(
            constraint_id="constraint_03",
            description="No proposal can move to output without minimum 2 peer validations",
            rule_fn=lambda e, l: peer_validation_rule(e, l, min_validations=2),
            applies_to_agents=["*"],
        )
    )

    return registry
