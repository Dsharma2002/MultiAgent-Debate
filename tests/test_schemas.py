"""Tests for Shared Vocabulary schemas and VocabularyRegistry."""

from uuid import uuid4

import pytest

from mad.schemas.vocabulary import (
    Proposal,
    VocabularyFieldSpec,
    VocabularyFieldType,
    VocabularyRegistry,
)


class TestVocabularyRegistry:
    """Test the VocabularyRegistry for exact-key enforcement."""

    def setup_method(self):
        self.registry = VocabularyRegistry()
        self.registry.register(
            "proposal_id",
            VocabularyFieldSpec(type=VocabularyFieldType.UUID, required=True),
        )
        self.registry.register(
            "tech_feasibility_score",
            VocabularyFieldSpec(
                type=VocabularyFieldType.FLOAT, min=0.0, max=1.0
            ),
        )
        self.registry.register(
            "budget_allocation",
            VocabularyFieldSpec(
                type=VocabularyFieldType.INTEGER, min=0, unit="USD"
            ),
        )
        self.registry.register(
            "description",
            VocabularyFieldSpec(type=VocabularyFieldType.STRING),
        )

    def test_valid_data_passes(self):
        data = {
            "proposal_id": str(uuid4()),
            "tech_feasibility_score": 0.8,
            "budget_allocation": 1000,
        }
        errors = self.registry.validate_data(data)
        assert errors == []

    def test_unapproved_key_rejected(self):
        """No synonyms allowed — 'cost' is not 'budget_allocation'."""
        data = {
            "proposal_id": str(uuid4()),
            "cost": 1000,  # Unapproved synonym
        }
        errors = self.registry.validate_data(data)
        assert any("Unapproved vocabulary keys" in e for e in errors)
        assert any("cost" in e for e in errors)

    def test_missing_required_key_rejected(self):
        data = {"budget_allocation": 1000}  # Missing required proposal_id
        errors = self.registry.validate_data(data)
        assert any("Missing required" in e for e in errors)

    def test_float_out_of_range_rejected(self):
        data = {
            "proposal_id": str(uuid4()),
            "tech_feasibility_score": 1.5,  # Exceeds max 1.0
        }
        errors = self.registry.validate_data(data)
        assert any("exceeds maximum" in e for e in errors)

    def test_negative_float_rejected(self):
        data = {
            "proposal_id": str(uuid4()),
            "tech_feasibility_score": -0.1,  # Below min 0.0
        }
        errors = self.registry.validate_data(data)
        assert any("below minimum" in e for e in errors)

    def test_wrong_type_rejected(self):
        data = {
            "proposal_id": str(uuid4()),
            "budget_allocation": "not_an_int",  # Wrong type
        }
        errors = self.registry.validate_data(data)
        assert any("expected type integer" in e for e in errors)

    def test_invalid_uuid_rejected(self):
        data = {
            "proposal_id": "not-a-valid-uuid",
        }
        errors = self.registry.validate_data(data)
        assert any("not a valid UUID" in e for e in errors)

    def test_approved_keys_property(self):
        assert "proposal_id" in self.registry.approved_keys
        assert "budget_allocation" in self.registry.approved_keys
        assert "cost" not in self.registry.approved_keys

    def test_required_keys_property(self):
        assert "proposal_id" in self.registry.required_keys
        assert "budget_allocation" not in self.registry.required_keys


class TestProposal:
    """Test the Proposal convenience model."""

    def test_valid_proposal(self):
        p = Proposal(
            proposal_id=str(uuid4()),
            tech_feasibility_score=0.85,
            budget_allocation=2000,
            description="Test proposal",
        )
        assert 0.0 <= p.tech_feasibility_score <= 1.0
        assert p.budget_allocation == 2000

    def test_invalid_feasibility_score(self):
        with pytest.raises(Exception):
            Proposal(
                proposal_id=str(uuid4()),
                tech_feasibility_score=1.5,  # Out of range
                budget_allocation=1000,
            )

    def test_invalid_proposal_id(self):
        with pytest.raises(Exception):
            Proposal(
                proposal_id="not-a-uuid",
                tech_feasibility_score=0.5,
                budget_allocation=1000,
            )

    def test_to_vocabulary_dict(self):
        pid = str(uuid4())
        p = Proposal(
            proposal_id=pid,
            tech_feasibility_score=0.7,
            budget_allocation=500,
        )
        d = p.to_vocabulary_dict()
        assert d["proposal_id"] == pid
        assert d["tech_feasibility_score"] == 0.7
        assert d["budget_allocation"] == 500

    def test_negative_budget_rejected(self):
        with pytest.raises(Exception):
            Proposal(
                proposal_id=str(uuid4()),
                tech_feasibility_score=0.5,
                budget_allocation=-100,
            )
