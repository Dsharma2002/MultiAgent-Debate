"""
Base Agent — Abstract base class for all agents in the system.

Each agent has:
- Core Specialty (70%): Private execution domain — the agent's primary function.
- Audit Mandate (30%): Cross-audit responsibility using specific constraints.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from mad.constraints.evaluator import ConstraintEvaluator
from mad.constraints.registry import ConstraintRegistry, ConstraintResult
from mad.ledger.base import LedgerBackend
from mad.schemas.evidence import EvidenceEntry


@dataclass
class AuditResult:
    """Result of an agent's cross-audit of another agent's entry."""

    approved: bool
    auditor_id: str
    comments: list[str] = field(default_factory=list)
    rejection_reasons: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        if self.approved:
            return f"APPROVED by {self.auditor_id}"
        return (
            f"REJECTED by {self.auditor_id}: "
            f"{'; '.join(self.rejection_reasons)}"
        )


# Agent class registry for dynamic loading
_AGENT_CLASS_REGISTRY: dict[str, type["BaseAgent"]] = {}


def register_agent(agent_type: str):
    """
    Decorator to register an agent class for YAML-driven instantiation.

    Usage:
        @register_agent("tech_lead")
        class TechLeadAgent(BaseAgent):
            ...
    """

    def decorator(cls: type[BaseAgent]) -> type[BaseAgent]:
        _AGENT_CLASS_REGISTRY[agent_type] = cls
        return cls

    return decorator


def get_registered_agents() -> dict[str, type["BaseAgent"]]:
    """Return the registry of all registered agent classes."""
    return dict(_AGENT_CLASS_REGISTRY)


class BaseAgent(ABC):
    """
    Abstract base class for all agents.

    Agents operate strictly within their Core Specialty and cannot
    generate content outside their declared domain. They communicate
    exclusively via the Truth Ledger.
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        core_specialty: str,
        audit_constraints: list[str],
        constraint_registry: ConstraintRegistry | None = None,
        system_prompt: str = "You are a specialized agent.",
        model: str = "gpt-4o",
    ) -> None:
        self.agent_id = agent_id
        self.name = name
        self.core_specialty = core_specialty
        self.audit_constraints = audit_constraints
        self.system_prompt = system_prompt
        self.model = model
        self._constraint_evaluator: ConstraintEvaluator | None = None

        if constraint_registry:
            self._constraint_evaluator = ConstraintEvaluator(constraint_registry)

    def set_constraint_registry(self, registry: ConstraintRegistry) -> None:
        """Set or update the constraint registry for this agent."""
        self._constraint_evaluator = ConstraintEvaluator(registry)

    def _execute_llm(self, user_prompt: str) -> dict[str, Any]:
        """
        Executes an LLM call using OpenAI's structured outputs.
        Requires OPENAI_API_KEY to be set in the environment.
        """
        import os
        from openai import OpenAI
        import json
        from mad.schemas.enterprise import AgentOutput
        
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            # Fallback for testing without an API key
            return {
                "summary": f"{self.name} mocked summary.",
                "claims": ["Mocked claim"],
                "assumptions": ["Mocked assumption"],
                "uncertainties": [],
                "evidence": ["Mocked evidence"],
                "recommended_next_action": "Proceed.",
                "blockers": []
            }

        client = OpenAI(api_key=api_key)
        response = client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=AgentOutput,
        )
        return json.loads(response.choices[0].message.content)

    def _execute_llm_audit(self, peer_entry_content: dict[str, Any]) -> dict[str, Any]:
        import os
        from openai import OpenAI
        import json
        from mad.schemas.enterprise import AuditOutput
        
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return {
                "approved": True,
                "rejection_reasons": []
            }

        client = OpenAI(api_key=api_key)
        audit_prompt = f"Audit the following peer entry for correctness, architectural soundness, and business alignment:\n{json.dumps(peer_entry_content, indent=2)}"
        
        response = client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": f"{self.system_prompt} Your task is to AUDIT upstream work."},
                {"role": "user", "content": audit_prompt},
            ],
            response_format=AuditOutput,
        )
        return json.loads(response.choices[0].message.content)

    @abstractmethod
    def core_execute(
        self,
        context: dict[str, Any],
        ledger: LedgerBackend,
    ) -> EvidenceEntry:
        """
        Generate a draft evidence entry within the agent's Core Specialty.

        This is the agent's primary function (70% of its role).
        The entry is a DRAFT — it has not been verified yet.

        Args:
            context: Task context (proposal details, requirements, etc.)
            ledger: Read access to the current Truth Ledger state

        Returns:
            A draft EvidenceEntry (verified_status=False)
        """
        ...

    def audit(
        self,
        entry: EvidenceEntry,
        ledger: LedgerBackend,
    ) -> AuditResult:
        """
        Cross-audit another agent's entry using this agent's Audit Mandate.

        This is the agent's secondary function (30% of its role).
        The agent checks the entry against its assigned constraint IDs.

        Can be overridden by subclasses for domain-specific audit logic
        beyond just constraint checking.
        """
        if not self._constraint_evaluator:
            return AuditResult(
                approved=False,
                auditor_id=self.agent_id,
                rejection_reasons=["No constraint registry configured for audit"],
            )

        # Evaluate using this agent's assigned constraints
        result = self._constraint_evaluator.evaluate_specific(
            entry=entry,
            ledger=ledger,
            constraint_ids=self.audit_constraints,
        )

        # Perform domain-specific audit checks
        domain_issues = self._domain_audit(entry, ledger)

        all_violations = result.violations + domain_issues
        return AuditResult(
            approved=len(all_violations) == 0,
            auditor_id=self.agent_id,
            rejection_reasons=all_violations,
        )

    def _domain_audit(
        self,
        entry: EvidenceEntry,
        ledger: LedgerBackend,
    ) -> list[str]:
        """
        Optional domain-specific audit checks beyond constraint evaluation.

        Override in subclasses to add specialty-specific validation.
        Returns a list of issue strings (empty if no issues found).
        """
        return []

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"id={self.agent_id!r}, "
            f"name={self.name!r}, "
            f"audit_constraints={self.audit_constraints})"
        )
