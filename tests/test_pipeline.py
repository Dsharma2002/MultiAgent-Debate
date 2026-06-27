"""Tests for the Verification Gate and Pipeline Orchestrator."""

from uuid import uuid4

import pytest

from mad.agents.base import BaseAgent, AuditResult
from mad.constraints.registry import create_default_registry
from mad.ledger.memory import InMemoryLedger
from mad.pipeline.gate import VerificationGate, GateResult
from mad.schemas.evidence import EvidenceEntry
from mad.schemas.vocabulary import VocabularyFieldSpec, VocabularyFieldType, VocabularyRegistry


class StubAgent(BaseAgent):
    """Stub agent for testing the pipeline."""

    def __init__(self, agent_id="stub", approve_all=True, **kwargs):
        super().__init__(
            agent_id=agent_id,
            name=f"Stub-{agent_id}",
            core_specialty="Testing",
            audit_constraints=[],
            **kwargs,
        )
        self._approve_all = approve_all

    def core_execute(self, context, ledger):
        return EvidenceEntry(
            author_agent_id=self.agent_id,
            content={
                "proposal_id": context.get("proposal_id", str(uuid4())),
                "budget_allocation": context.get("budget_allocation", 100),
                "description": "Stub output",
            },
            verified_status=False,
        )

    def audit(self, entry, ledger):
        if self._approve_all:
            return AuditResult(approved=True, auditor_id=self.agent_id)
        return AuditResult(
            approved=False,
            auditor_id=self.agent_id,
            rejection_reasons=["Stub rejection"],
        )


def _make_vocab_registry():
    """Create a vocabulary registry matching the test entries."""
    reg = VocabularyRegistry()
    reg.register("proposal_id", VocabularyFieldSpec(type=VocabularyFieldType.UUID, required=True))
    reg.register("budget_allocation", VocabularyFieldSpec(type=VocabularyFieldType.INTEGER))
    reg.register("description", VocabularyFieldSpec(type=VocabularyFieldType.STRING))
    reg.register("peer_validations", VocabularyFieldSpec(type=VocabularyFieldType.INTEGER))
    return reg


class TestVerificationGate:
    """Test the Verification Gate — the central enforcement point."""

    def setup_method(self):
        self.vocab = _make_vocab_registry()
        self.constraints = create_default_registry()
        self.ledger = InMemoryLedger()
        self.gate = VerificationGate(
            vocabulary=self.vocab,
            constraint_registry=self.constraints,
            ledger=self.ledger,
            min_peer_validations=2,
        )

    def test_valid_entry_committed(self):
        """Entry that passes all checks should be committed."""
        draft = EvidenceEntry(
            author_agent_id="tech_lead",
            content={
                "proposal_id": str(uuid4()),
                "budget_allocation": 500,
                "description": "Valid entry",
            },
            verified_status=False,
        )
        peers = [
            StubAgent("peer1", approve_all=True),
            StubAgent("peer2", approve_all=True),
            StubAgent("peer3", approve_all=True),
        ]

        result = self.gate.verify(draft, peers)
        assert result.committed is True
        assert result.entry is not None
        assert result.entry.verified_status is True
        assert result.peer_validation_count >= 2

    def test_vocabulary_violation_rejected(self):
        """Entry with unapproved keys should be rejected."""
        draft = EvidenceEntry(
            author_agent_id="tech_lead",
            content={
                "proposal_id": str(uuid4()),
                "cost": 500,  # Unapproved key
            },
            verified_status=False,
        )
        peers = [StubAgent("peer1"), StubAgent("peer2")]

        result = self.gate.verify(draft, peers)
        assert result.committed is False
        assert any("Vocabulary" in e for e in result.errors)

    def test_budget_constraint_violation_rejected(self):
        """Entry exceeding budget should be rejected."""
        # Fill most of the budget
        self.ledger.append(EvidenceEntry(
            author_agent_id="a1",
            content={"budget_allocation": 4500},
            verified_status=True,
        ))

        draft = EvidenceEntry(
            author_agent_id="tech_lead",
            content={
                "proposal_id": str(uuid4()),
                "budget_allocation": 1000,
                "description": "Over budget",
            },
            verified_status=False,
        )
        peers = [StubAgent("peer1"), StubAgent("peer2")]

        result = self.gate.verify(draft, peers)
        assert result.committed is False
        assert any("constraint_01" in e for e in result.errors)

    def test_insufficient_peer_validations_rejected(self):
        """Entry without enough peer approvals should be rejected."""
        draft = EvidenceEntry(
            author_agent_id="tech_lead",
            content={
                "proposal_id": str(uuid4()),
                "budget_allocation": 100,
                "description": "Needs peers",
            },
            verified_status=False,
        )
        # Only 1 approving peer, but need 2
        peers = [
            StubAgent("peer1", approve_all=True),
            StubAgent("peer2", approve_all=False),
            StubAgent("peer3", approve_all=False),
        ]

        result = self.gate.verify(draft, peers)
        assert result.committed is False
        assert any("Insufficient approvals" in e for e in result.errors)

    def test_self_audit_skipped(self):
        """An agent should not audit its own entry."""
        draft = EvidenceEntry(
            author_agent_id="self_agent",
            content={
                "proposal_id": str(uuid4()),
                "budget_allocation": 100,
            },
            verified_status=False,
        )
        # Include the author as a peer — should be skipped
        peers = [
            StubAgent("self_agent", approve_all=True),
            StubAgent("peer1", approve_all=True),
            StubAgent("peer2", approve_all=True),
        ]

        result = self.gate.verify(draft, peers)
        # self_agent audit skipped, peer1 and peer2 approve = 2 validations
        assert result.committed is True
        assert result.peer_validation_count == 2

    def test_committed_entry_has_peer_validation_count(self):
        """Committed entry should include peer_validations in its content."""
        draft = EvidenceEntry(
            author_agent_id="tech_lead",
            content={
                "proposal_id": str(uuid4()),
                "budget_allocation": 100,
            },
            verified_status=False,
        )
        peers = [
            StubAgent("peer1", approve_all=True),
            StubAgent("peer2", approve_all=True),
        ]

        result = self.gate.verify(draft, peers)
        assert result.committed is True
        assert result.entry.content["peer_validations"] >= 2

    def test_committed_entry_is_in_ledger(self):
        """Committed entry should be retrievable from the ledger."""
        draft = EvidenceEntry(
            author_agent_id="tech_lead",
            content={
                "proposal_id": str(uuid4()),
                "budget_allocation": 100,
            },
            verified_status=False,
        )
        peers = [StubAgent("p1"), StubAgent("p2")]

        result = self.gate.verify(draft, peers)
        assert result.committed is True
        assert self.ledger.size() == 1

        stored = self.ledger.get(result.entry.entry_id)
        assert stored is not None
        assert stored.verified_status is True
