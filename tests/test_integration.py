"""
End-to-end integration tests.

These tests run the complete pipeline with real agents, config files,
and verification — validating the full system works together.
"""

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from mad.ledger.memory import InMemoryLedger
from mad.ledger.integrity import verify_chain
from mad.pipeline.orchestrator import PipelineOrchestrator, PipelineResult


# Path to the config directory
CONFIG_DIR = str(Path(__file__).parent.parent / "config")


class TestEndToEndPipeline:
    """Full integration tests with real agents and config."""

    def test_standard_proposal_pipeline(self):
        """A standard proposal should pass through all 4 agents."""
        ledger = InMemoryLedger()
        orchestrator = PipelineOrchestrator.from_config(
            config_dir=CONFIG_DIR,
            ledger=ledger,
        )

        context = {
            "proposal_id": str(uuid4()),
            "description": "Build a REST API for user management",
            "budget_allocation": 1000,
            "complexity": "medium",
            "user_impact": "high",
            "effort": "medium",
        }

        result = orchestrator.run(context)

        assert isinstance(result, PipelineResult)
        assert len(result.step_results) == 11  # All 11 agents ran

        # At least some entries should be committed
        assert result.ledger_snapshot is not None
        assert result.ledger_snapshot.total_entries > 0

    def test_ledger_integrity_after_pipeline(self):
        """The ledger's hash chain should be valid after pipeline execution."""
        ledger = InMemoryLedger()
        orchestrator = PipelineOrchestrator.from_config(
            config_dir=CONFIG_DIR,
            ledger=ledger,
        )

        context = {
            "proposal_id": str(uuid4()),
            "description": "Implement caching layer with Redis",
            "budget_allocation": 800,
        }

        result = orchestrator.run(context)
        entries = ledger.get_all()

        if entries:
            is_valid, errors = verify_chain(entries)
            assert is_valid is True, f"Chain integrity errors: {errors}"

    def test_budget_enforcement_across_pipeline(self):
        """Budget constraint should be enforced across multiple proposals."""
        ledger = InMemoryLedger()
        orchestrator = PipelineOrchestrator.from_config(
            config_dir=CONFIG_DIR,
            ledger=ledger,
        )

        # First proposal uses $2000
        context1 = {
            "proposal_id": str(uuid4()),
            "description": "Phase 1: Database migration",
            "budget_allocation": 2000,
        }
        result1 = orchestrator.run(context1)

        # Second proposal uses $2000 more
        context2 = {
            "proposal_id": str(uuid4()),
            "description": "Phase 2: API implementation",
            "budget_allocation": 2000,
        }
        result2 = orchestrator.run(context2)

        # Total budget should not exceed $5000
        total_budget = ledger.get_total_budget()
        assert total_budget <= 5000

    def test_sequential_execution_enforced(self):
        """Each agent should only execute after the previous one is done."""
        ledger = InMemoryLedger()
        orchestrator = PipelineOrchestrator.from_config(
            config_dir=CONFIG_DIR,
            ledger=ledger,
        )

        context = {
            "proposal_id": str(uuid4()),
            "description": "Simple feature addition",
            "budget_allocation": 500,
        }

        result = orchestrator.run(context)

        # Verify steps ran in order
        expected_order = [
            "discovery", "business_analyst", "solution_deviser", "technical_architect",
            "data_integration", "builder", "test_qa", "verifier",
            "business_reviewer", "compliance_risk", "synthesizer"
        ]
        actual_order = [s.agent_id for s in result.step_results]
        assert actual_order == expected_order

    def test_verified_entries_are_immutable(self):
        """Once committed, entries should maintain their hash integrity."""
        ledger = InMemoryLedger()
        orchestrator = PipelineOrchestrator.from_config(
            config_dir=CONFIG_DIR,
            ledger=ledger,
        )

        context = {
            "proposal_id": str(uuid4()),
            "description": "Test immutability",
            "budget_allocation": 100,
        }

        orchestrator.run(context)

        for entry in ledger.get_all():
            assert entry.verify_integrity(), (
                f"Entry {entry.entry_id} hash mismatch after pipeline"
            )

    def test_pipeline_result_summary(self):
        """Pipeline result should provide a useful summary."""
        ledger = InMemoryLedger()
        orchestrator = PipelineOrchestrator.from_config(
            config_dir=CONFIG_DIR,
            ledger=ledger,
        )

        context = {
            "proposal_id": str(uuid4()),
            "description": "Summary test",
            "budget_allocation": 300,
        }

        result = orchestrator.run(context)
        summary = result.summary()

        assert "success" in summary
        assert "steps_completed" in summary
        assert "steps_failed" in summary
        assert "total_steps" in summary
        assert summary["total_steps"] == 11
