"""
QA Engineer Agent — specializes in edge-case identification and test coverage.

Core Specialty (70%): Edge-case identification, unit test parameters, error handling.
Audit Mandate (30%): Cross-audits using Constraint_03 (peer validations).
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from mad.agents.base import BaseAgent, register_agent
from mad.ledger.base import LedgerBackend
from mad.schemas.evidence import EvidenceEntry


@register_agent("qa_engineer")
class QAEngineerAgent(BaseAgent):
    """
    Agent specializing in quality assurance, testing, and edge-case analysis.

    Evaluates proposals for robustness, error handling, and test coverage.
    Identifies potential failure modes and missing fallback protocols.
    """

    def core_execute(
        self,
        context: dict[str, Any],
        ledger: LedgerBackend,
    ) -> EvidenceEntry:
        """
        Generate a quality assessment with identified edge cases and test requirements.
        """
        proposal_id = context.get("proposal_id", str(uuid4()))
        description = context.get("description", "")
        budget = context.get("budget_allocation", 0)

        # QA analysis
        edge_cases = self._identify_edge_cases(context, ledger)
        test_requirements = self._define_test_requirements(context, ledger)
        risk_assessment = self._assess_risk(context, ledger)

        content: dict[str, Any] = {
            "proposal_id": proposal_id,
            "tech_feasibility_score": context.get("tech_feasibility_score", 0.5),
            "budget_allocation": budget,
            "description": f"[QA Assessment] {description}",
            "assessment_type": "quality_assurance",
            "edge_cases": edge_cases,
            "test_requirements": test_requirements,
            "risk_level": risk_assessment,
        }

        if "metadata" in context:
            content["metadata"] = context["metadata"]

        return EvidenceEntry(
            author_agent_id=self.agent_id,
            content=content,
            verified_status=False,
        )

    def _identify_edge_cases(
        self,
        context: dict[str, Any],
        ledger: LedgerBackend,
    ) -> list[str]:
        """Identify potential edge cases based on the proposal."""
        edge_cases: list[str] = []

        # Budget edge cases
        budget = context.get("budget_allocation", 0)
        if budget == 0:
            edge_cases.append("Zero budget — may lack resources for proper implementation")
        elif budget > 3000:
            edge_cases.append("High budget — needs extra scrutiny for cost overruns")

        # Scale edge cases
        if context.get("scale_requirements"):
            edge_cases.append(
                f"Scale requirements ({context['scale_requirements']}) — "
                f"verify behavior under peak load"
            )

        # Dependency edge cases from ledger
        verified = ledger.get_all(verified_only=True)
        if len(verified) > 3:
            edge_cases.append(
                f"Complex dependency chain ({len(verified)} prior entries) — "
                f"verify integration behavior"
            )

        # Generic edge cases
        edge_cases.extend([
            "Input validation — verify handling of malformed inputs",
            "Timeout/retry — verify behavior on downstream service failures",
            "Concurrent access — verify thread safety if applicable",
        ])

        return edge_cases

    def _define_test_requirements(
        self,
        context: dict[str, Any],
        ledger: LedgerBackend,
    ) -> list[str]:
        """Define test requirements for the proposal."""
        requirements: list[str] = [
            "Unit tests for all core logic paths",
            "Integration tests for cross-component interactions",
            "Error handling tests for all failure modes",
        ]

        if context.get("database"):
            requirements.append("Database migration rollback tests")

        if context.get("scale_requirements"):
            requirements.append("Load/stress tests for scale requirements")

        return requirements

    def _assess_risk(
        self,
        context: dict[str, Any],
        ledger: LedgerBackend,
    ) -> str:
        """Assess overall risk level."""
        risk_factors = 0

        if context.get("complexity") == "high":
            risk_factors += 2
        elif context.get("complexity") == "medium":
            risk_factors += 1

        budget = context.get("budget_allocation", 0)
        if budget > 3000:
            risk_factors += 1

        if context.get("scale_requirements"):
            risk_factors += 1

        if risk_factors >= 3:
            return "HIGH"
        elif risk_factors >= 1:
            return "MEDIUM"
        return "LOW"

    def _domain_audit(
        self,
        entry: EvidenceEntry,
        ledger: LedgerBackend,
    ) -> list[str]:
        """QA audit: check for missing error handling and fallback protocols."""
        issues: list[str] = []

        content = entry.content

        # Check if entry has error handling considerations
        if content.get("assessment_type") == "technical_feasibility":
            if not content.get("architecture_notes"):
                issues.append(
                    "Technical assessment lacks architecture notes — "
                    "cannot verify error handling strategy"
                )

        return issues
