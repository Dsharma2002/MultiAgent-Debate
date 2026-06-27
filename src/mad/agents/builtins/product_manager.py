"""
Product Manager Agent — specializes in feature prioritization and business value.

Core Specialty (70%): Feature prioritisation, user value metrics, business ROI.
Audit Mandate (30%): Cross-audits using Constraint_01 (budget limits).
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from mad.agents.base import BaseAgent, register_agent
from mad.ledger.base import LedgerBackend
from mad.schemas.evidence import EvidenceEntry


@register_agent("product_manager")
class ProductManagerAgent(BaseAgent):
    """
    Agent specializing in product strategy and business value assessment.

    Evaluates proposals from a user-value and ROI perspective,
    assessing market fit, priority, and resource allocation.
    """

    def core_execute(
        self,
        context: dict[str, Any],
        ledger: LedgerBackend,
    ) -> EvidenceEntry:
        """
        Generate a product/business value assessment.

        Produces an evidence entry with prioritization scores,
        budget recommendations, and ROI analysis.
        """
        proposal_id = context.get("proposal_id", str(uuid4()))
        description = context.get("description", "")
        budget = context.get("budget_allocation", 0)

        # Business value assessment
        priority_score = self._assess_priority(context, ledger)
        roi_assessment = self._assess_roi(context, ledger)
        recommended_budget = self._recommend_budget(context, ledger)

        content: dict[str, Any] = {
            "proposal_id": proposal_id,
            "tech_feasibility_score": context.get("tech_feasibility_score", 0.5),
            "budget_allocation": recommended_budget,
            "description": f"[Product Assessment] {description}",
            "assessment_type": "product_value",
            "priority_score": priority_score,
            "roi_assessment": roi_assessment,
        }

        if "metadata" in context:
            content["metadata"] = context["metadata"]

        return EvidenceEntry(
            author_agent_id=self.agent_id,
            content=content,
            verified_status=False,
        )

    def _assess_priority(
        self,
        context: dict[str, Any],
        ledger: LedgerBackend,
    ) -> str:
        """Determine feature priority based on user impact and effort."""
        user_impact = context.get("user_impact", "medium")
        effort = context.get("effort", "medium")

        # Simple priority matrix
        priority_matrix = {
            ("high", "low"): "P0-critical",
            ("high", "medium"): "P1-high",
            ("high", "high"): "P2-medium",
            ("medium", "low"): "P1-high",
            ("medium", "medium"): "P2-medium",
            ("medium", "high"): "P3-low",
            ("low", "low"): "P2-medium",
            ("low", "medium"): "P3-low",
            ("low", "high"): "P4-backlog",
        }

        return priority_matrix.get((user_impact, effort), "P2-medium")

    def _assess_roi(
        self,
        context: dict[str, Any],
        ledger: LedgerBackend,
    ) -> str:
        """Assess return on investment."""
        budget = context.get("budget_allocation", 0)
        user_impact = context.get("user_impact", "medium")

        if budget == 0:
            return "N/A — no budget allocated"

        impact_multiplier = {"high": 3.0, "medium": 1.5, "low": 0.5}
        multiplier = impact_multiplier.get(user_impact, 1.5)

        estimated_value = budget * multiplier
        roi_ratio = estimated_value / budget if budget > 0 else 0

        if roi_ratio >= 2.5:
            return f"Excellent ROI ({roi_ratio:.1f}x)"
        elif roi_ratio >= 1.5:
            return f"Good ROI ({roi_ratio:.1f}x)"
        else:
            return f"Marginal ROI ({roi_ratio:.1f}x)"

    def _recommend_budget(
        self,
        context: dict[str, Any],
        ledger: LedgerBackend,
    ) -> int:
        """Recommend a budget allocation considering current ledger state."""
        requested_budget = context.get("budget_allocation", 0)
        current_total = ledger.get_total_budget()
        remaining = 5000 - current_total

        if requested_budget > remaining:
            # Cap at remaining budget
            return max(0, remaining)

        return requested_budget

    def _domain_audit(
        self,
        entry: EvidenceEntry,
        ledger: LedgerBackend,
    ) -> list[str]:
        """PM audit: verify budget makes business sense."""
        issues: list[str] = []

        budget = entry.content.get("budget_allocation", 0)
        if isinstance(budget, int) and budget > 0:
            current_total = ledger.get_total_budget()
            remaining = 5000 - current_total
            utilization = (current_total + budget) / 5000

            if utilization > 0.9:
                issues.append(
                    f"Budget allocation of ${budget} would use {utilization:.0%} "
                    f"of total budget — consider reducing"
                )

        return issues
