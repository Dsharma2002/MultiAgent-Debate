"""
Tech Lead Agent — specializes in backend architecture and technical feasibility.

Core Specialty (70%): Database optimization, backend architecture, execution limits.
Audit Mandate (30%): Cross-audits using Constraint_01 (budget) and Constraint_03 (peer validations).
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from mad.agents.base import BaseAgent, register_agent
from mad.ledger.base import LedgerBackend
from mad.schemas.evidence import EvidenceEntry


@register_agent("tech_lead")
class TechLeadAgent(BaseAgent):
    """
    Agent specializing in technical architecture decisions.

    Evaluates proposals from a backend/infrastructure perspective,
    assessing feasibility, performance implications, and technical debt.
    """

    def core_execute(
        self,
        context: dict[str, Any],
        ledger: LedgerBackend,
    ) -> EvidenceEntry:
        """
        Generate a technical feasibility assessment.

        Reads the proposal from context and produces an evidence entry
        with a tech_feasibility_score and architecture notes.
        """
        proposal_id = context.get("proposal_id", str(uuid4()))
        description = context.get("description", "")
        budget = context.get("budget_allocation", 0)

        # Technical assessment logic
        feasibility_score = self._assess_feasibility(context, ledger)
        arch_notes = self._generate_arch_notes(context, ledger)

        content: dict[str, Any] = {
            "proposal_id": proposal_id,
            "tech_feasibility_score": feasibility_score,
            "budget_allocation": budget,
            "description": f"[Tech Assessment] {description}",
            "assessment_type": "technical_feasibility",
            "architecture_notes": arch_notes,
        }

        # Add metadata if provided
        if "metadata" in context:
            content["metadata"] = context["metadata"]

        return EvidenceEntry(
            author_agent_id=self.agent_id,
            content=content,
            verified_status=False,
        )

    def _assess_feasibility(
        self,
        context: dict[str, Any],
        ledger: LedgerBackend,
    ) -> float:
        """
        Assess technical feasibility based on context and ledger state.

        Uses heuristics for rule-based operation. When LLM integration
        is enabled, this can be replaced with LLM-driven reasoning.
        """
        score = 0.7  # Base feasibility score

        budget = context.get("budget_allocation", 0)

        # Budget-relative feasibility adjustment
        if budget > 0:
            current_total = ledger.get_total_budget()
            budget_utilization = (current_total + budget) / 5000
            if budget_utilization > 0.8:
                score -= 0.2  # High budget utilization reduces feasibility
            elif budget_utilization < 0.3:
                score += 0.1  # Low utilization suggests room for investment

        # Complexity factor from context
        complexity = context.get("complexity", "medium")
        if complexity == "high":
            score -= 0.15
        elif complexity == "low":
            score += 0.1

        # Clamp to valid range
        return max(0.0, min(1.0, round(score, 2)))

    def _generate_arch_notes(
        self,
        context: dict[str, Any],
        ledger: LedgerBackend,
    ) -> str:
        """Generate architecture notes based on the proposal context."""
        notes: list[str] = []

        if context.get("database"):
            notes.append(f"Database consideration: {context['database']}")

        if context.get("scale_requirements"):
            notes.append(f"Scale requirements: {context['scale_requirements']}")

        # Review existing verified entries for dependency conflicts
        verified = ledger.get_all(verified_only=True)
        if verified:
            notes.append(
                f"Ledger context: {len(verified)} verified entries inform this assessment"
            )

        return "; ".join(notes) if notes else "Standard architecture review completed"

    def _domain_audit(
        self,
        entry: EvidenceEntry,
        ledger: LedgerBackend,
    ) -> list[str]:
        """Tech Lead audit: check for backend feasibility concerns."""
        issues: list[str] = []

        score = entry.content.get("tech_feasibility_score")
        if isinstance(score, (int, float)) and score < 0.3:
            issues.append(
                f"Technical feasibility score {score} is critically low — "
                f"proposal may not be implementable"
            )

        return issues
