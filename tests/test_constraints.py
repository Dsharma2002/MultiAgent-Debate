"""Tests for Shared Constraints — registry and evaluator."""

from uuid import uuid4

import pytest

from mad.constraints.evaluator import ConstraintEvaluator
from mad.constraints.registry import (
    Constraint,
    ConstraintRegistry,
    budget_limit_rule,
    create_default_registry,
    peer_validation_rule,
    security_boundary_rule,
)
from mad.ledger.memory import InMemoryLedger
from mad.schemas.evidence import EvidenceEntry


def _make_entry(
    agent_id: str = "test_agent",
    budget: int = 100,
    security_class: str | None = None,
    peer_validations: int | None = None,
) -> EvidenceEntry:
    content: dict = {
        "proposal_id": str(uuid4()),
        "budget_allocation": budget,
    }
    if security_class:
        content["security_classification"] = security_class
    if peer_validations is not None:
        content["peer_validations"] = peer_validations
    return EvidenceEntry(
        author_agent_id=agent_id,
        content=content,
        verified_status=False,
    )


class TestConstraintRegistry:
    """Test constraint registration and lookup."""

    def test_register_and_get(self):
        registry = ConstraintRegistry()
        c = Constraint(
            constraint_id="test_01",
            description="Test constraint",
            rule_fn=lambda e, l: (True, None),
        )
        registry.register(c)
        assert registry.get("test_01") is not None
        assert len(registry) == 1

    def test_get_for_agent_wildcard(self):
        registry = ConstraintRegistry()
        c = Constraint(
            constraint_id="c1",
            description="Wildcard",
            rule_fn=lambda e, l: (True, None),
            applies_to_agents=["*"],
        )
        registry.register(c)
        assert len(registry.get_for_agent("any_agent")) == 1

    def test_get_for_agent_specific(self):
        registry = ConstraintRegistry()
        c = Constraint(
            constraint_id="c1",
            description="Specific",
            rule_fn=lambda e, l: (True, None),
            applies_to_agents=["tech_lead"],
        )
        registry.register(c)
        assert len(registry.get_for_agent("tech_lead")) == 1
        assert len(registry.get_for_agent("pm")) == 0

    def test_default_registry_has_3_constraints(self):
        registry = create_default_registry()
        assert len(registry) == 3


class TestBudgetLimitRule:
    """Test Constraint_01: Total budget allocation limit."""

    def test_within_budget(self):
        ledger = InMemoryLedger()
        entry = _make_entry(budget=1000)
        passed, reason = budget_limit_rule(entry, ledger, max_budget=5000)
        assert passed is True

    def test_exceeds_budget(self):
        ledger = InMemoryLedger()
        # Add existing budget
        ledger.append(EvidenceEntry(
            author_agent_id="a1",
            content={"budget_allocation": 4000},
            verified_status=True,
        ))
        entry = _make_entry(budget=1500)
        passed, reason = budget_limit_rule(entry, ledger, max_budget=5000)
        assert passed is False
        assert "exceeds limit" in reason

    def test_exact_budget_limit(self):
        ledger = InMemoryLedger()
        entry = _make_entry(budget=5000)
        passed, reason = budget_limit_rule(entry, ledger, max_budget=5000)
        assert passed is True  # Exactly at limit is OK

    def test_zero_budget(self):
        ledger = InMemoryLedger()
        entry = _make_entry(budget=0)
        passed, reason = budget_limit_rule(entry, ledger, max_budget=5000)
        assert passed is True


class TestSecurityBoundaryRule:
    """Test Constraint_02: Security classification boundaries."""

    def test_non_restricted_agent_passes(self):
        ledger = InMemoryLedger()
        entry = _make_entry(
            agent_id="tech_lead", security_class="high"
        )
        passed, reason = security_boundary_rule(entry, ledger)
        assert passed is True

    def test_restricted_agent_with_high_security_fails(self):
        ledger = InMemoryLedger()
        entry = _make_entry(
            agent_id="qa_engineer", security_class="high"
        )
        passed, reason = security_boundary_rule(entry, ledger)
        assert passed is False
        assert "not authorized" in reason

    def test_restricted_agent_with_standard_security_passes(self):
        ledger = InMemoryLedger()
        entry = _make_entry(
            agent_id="qa_engineer", security_class="standard"
        )
        passed, reason = security_boundary_rule(entry, ledger)
        assert passed is True

    def test_no_security_class_passes(self):
        ledger = InMemoryLedger()
        entry = _make_entry(agent_id="qa_engineer")
        passed, reason = security_boundary_rule(entry, ledger)
        assert passed is True


class TestPeerValidationRule:
    """Test Constraint_03: Minimum peer validations."""

    def test_sufficient_validations(self):
        ledger = InMemoryLedger()
        entry = _make_entry(peer_validations=3)
        passed, reason = peer_validation_rule(entry, ledger, min_validations=2)
        assert passed is True

    def test_insufficient_validations(self):
        ledger = InMemoryLedger()
        entry = _make_entry(peer_validations=1)
        passed, reason = peer_validation_rule(entry, ledger, min_validations=2)
        assert passed is False

    def test_no_peer_validations_field_deferred(self):
        """If field not present, defer to pipeline audit phase."""
        ledger = InMemoryLedger()
        entry = _make_entry()  # No peer_validations field
        passed, reason = peer_validation_rule(entry, ledger)
        assert passed is True  # Deferred


class TestConstraintEvaluator:
    """Test the constraint evaluator engine."""

    def test_all_constraints_pass(self):
        registry = create_default_registry()
        evaluator = ConstraintEvaluator(registry)
        ledger = InMemoryLedger()

        entry = _make_entry(agent_id="tech_lead", budget=1000)
        result = evaluator.evaluate(entry, ledger)
        assert result.passed is True

    def test_budget_violation_caught(self):
        registry = create_default_registry()
        evaluator = ConstraintEvaluator(registry)
        ledger = InMemoryLedger()

        # Fill budget
        ledger.append(EvidenceEntry(
            author_agent_id="a1",
            content={"budget_allocation": 4500},
            verified_status=True,
        ))

        entry = _make_entry(budget=1000)
        result = evaluator.evaluate(entry, ledger)
        assert result.passed is False
        assert any("constraint_01" in v for v in result.violations)

    def test_evaluate_specific_constraints(self):
        registry = create_default_registry()
        evaluator = ConstraintEvaluator(registry)
        ledger = InMemoryLedger()

        entry = _make_entry(budget=100)
        result = evaluator.evaluate_specific(
            entry, ledger, constraint_ids=["constraint_01"]
        )
        assert result.passed is True

    def test_unknown_constraint_id(self):
        registry = create_default_registry()
        evaluator = ConstraintEvaluator(registry)
        ledger = InMemoryLedger()

        entry = _make_entry()
        result = evaluator.evaluate_specific(
            entry, ledger, constraint_ids=["nonexistent"]
        )
        assert result.passed is False
        assert any("Unknown constraint" in v for v in result.violations)
