"""Tests for Agent base class, builtins, and loader."""

from uuid import uuid4

import pytest

from mad.agents.base import AuditResult, BaseAgent, register_agent, get_registered_agents
from mad.constraints.registry import create_default_registry
from mad.ledger.memory import InMemoryLedger
from mad.schemas.evidence import EvidenceEntry

# Import builtins to trigger registration
from mad.agents.builtins.tech_lead import TechLeadAgent
from mad.agents.builtins.product_manager import ProductManagerAgent
from mad.agents.builtins.qa_engineer import QAEngineerAgent
from mad.agents.builtins.security_auditor import SecurityAuditorAgent


def _make_context(**kwargs) -> dict:
    """Create a minimal task context."""
    base = {
        "proposal_id": str(uuid4()),
        "description": "Test proposal",
        "budget_allocation": 1000,
    }
    base.update(kwargs)
    return base


class TestAgentRegistration:
    """Test the agent class registry system."""

    def test_builtins_are_registered(self):
        registered = get_registered_agents()
        assert "tech_lead" in registered
        assert "product_manager" in registered
        assert "qa_engineer" in registered
        assert "security_auditor" in registered

    def test_registered_classes_are_correct(self):
        registered = get_registered_agents()
        assert registered["tech_lead"] is TechLeadAgent
        assert registered["product_manager"] is ProductManagerAgent


class TestTechLeadAgent:
    """Test Tech Lead agent functionality."""

    def setup_method(self):
        self.registry = create_default_registry()
        self.agent = TechLeadAgent(
            agent_id="tech_lead",
            name="Tech Lead",
            core_specialty="Backend architecture",
            audit_constraints=["constraint_01", "constraint_03"],
            constraint_registry=self.registry,
        )
        self.ledger = InMemoryLedger()

    def test_core_execute_produces_draft(self):
        context = _make_context()
        entry = self.agent.core_execute(context, self.ledger)

        assert isinstance(entry, EvidenceEntry)
        assert entry.author_agent_id == "tech_lead"
        assert entry.verified_status is False
        assert "tech_feasibility_score" in entry.content
        assert entry.content["assessment_type"] == "technical_feasibility"

    def test_feasibility_score_in_valid_range(self):
        context = _make_context()
        entry = self.agent.core_execute(context, self.ledger)
        score = entry.content["tech_feasibility_score"]
        assert 0.0 <= score <= 1.0

    def test_audit_approves_valid_entry(self):
        other_entry = EvidenceEntry(
            author_agent_id="product_manager",
            content={
                "proposal_id": str(uuid4()),
                "budget_allocation": 500,
                "tech_feasibility_score": 0.7,
            },
            verified_status=False,
        )
        result = self.agent.audit(other_entry, self.ledger)
        assert isinstance(result, AuditResult)
        assert result.auditor_id == "tech_lead"

    def test_domain_audit_flags_low_feasibility(self):
        entry = EvidenceEntry(
            author_agent_id="product_manager",
            content={
                "proposal_id": str(uuid4()),
                "tech_feasibility_score": 0.1,  # Critically low
                "budget_allocation": 100,
            },
            verified_status=False,
        )
        issues = self.agent._domain_audit(entry, self.ledger)
        assert any("critically low" in issue for issue in issues)


class TestProductManagerAgent:
    """Test Product Manager agent functionality."""

    def setup_method(self):
        self.registry = create_default_registry()
        self.agent = ProductManagerAgent(
            agent_id="product_manager",
            name="Product Manager",
            core_specialty="Feature prioritisation",
            audit_constraints=["constraint_01"],
            constraint_registry=self.registry,
        )
        self.ledger = InMemoryLedger()

    def test_core_execute_produces_assessment(self):
        context = _make_context(user_impact="high", effort="low")
        entry = self.agent.core_execute(context, self.ledger)

        assert entry.content["assessment_type"] == "product_value"
        assert entry.content["priority_score"] == "P0-critical"

    def test_budget_capped_to_remaining(self):
        # Fill most of the budget
        self.ledger.append(EvidenceEntry(
            author_agent_id="a1",
            content={"budget_allocation": 4500},
            verified_status=True,
        ))
        context = _make_context(budget_allocation=1000)
        entry = self.agent.core_execute(context, self.ledger)
        # Should cap budget to remaining (500)
        assert entry.content["budget_allocation"] <= 500


class TestQAEngineerAgent:
    """Test QA Engineer agent functionality."""

    def setup_method(self):
        self.registry = create_default_registry()
        self.agent = QAEngineerAgent(
            agent_id="qa_engineer",
            name="QA Engineer",
            core_specialty="Edge-case identification",
            audit_constraints=["constraint_03"],
            constraint_registry=self.registry,
        )
        self.ledger = InMemoryLedger()

    def test_core_execute_identifies_edge_cases(self):
        context = _make_context(complexity="high")
        entry = self.agent.core_execute(context, self.ledger)

        assert entry.content["assessment_type"] == "quality_assurance"
        assert len(entry.content["edge_cases"]) > 0
        assert len(entry.content["test_requirements"]) > 0

    def test_high_complexity_means_high_risk(self):
        context = _make_context(
            complexity="high",
            budget_allocation=4000,
            scale_requirements="10k connections",
        )
        entry = self.agent.core_execute(context, self.ledger)
        assert entry.content["risk_level"] == "HIGH"


class TestSecurityAuditorAgent:
    """Test Security Auditor agent functionality."""

    def setup_method(self):
        self.registry = create_default_registry()
        self.agent = SecurityAuditorAgent(
            agent_id="security_auditor",
            name="Security Auditor",
            core_specialty="Threat modeling",
            audit_constraints=["constraint_02"],
            constraint_registry=self.registry,
        )
        self.ledger = InMemoryLedger()

    def test_core_execute_produces_security_assessment(self):
        context = _make_context(
            description="Implement authentication with JWT tokens"
        )
        entry = self.agent.core_execute(context, self.ledger)

        assert entry.content["assessment_type"] == "security_audit"
        assert len(entry.content["identified_threats"]) > 0
        assert len(entry.content["security_recommendations"]) > 0

    def test_security_classification_inferred(self):
        context = _make_context(
            description="Handle PII personal data for user profiles"
        )
        entry = self.agent.core_execute(context, self.ledger)
        assert entry.content["security_classification"] == "high"

    def test_domain_audit_flags_non_security_agent_handling_sensitive(self):
        entry = EvidenceEntry(
            author_agent_id="qa_engineer",
            content={
                "proposal_id": str(uuid4()),
                "description": "Handle password storage and encryption",
                "budget_allocation": 100,
            },
            verified_status=False,
        )
        issues = self.agent._domain_audit(entry, self.ledger)
        assert any("security-sensitive" in issue for issue in issues)
