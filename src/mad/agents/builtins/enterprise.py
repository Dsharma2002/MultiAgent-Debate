"""
Enterprise Agent Implementations — Production-grade agents with LangChain integration.

Each agent uses:
1. World-class system prompts from prompts.py
2. LangChain ChatOpenAI with structured output
3. The @register_agent decorator for backward compatibility with the YAML loader

These classes are used by the legacy orchestrator for backward compatibility.
The primary execution path uses the LangGraph node functions in graph.py.
"""

import json
import os
from typing import Any

from mad.agents.base import BaseAgent, register_agent, AuditResult
from mad.agents.prompts import AGENT_PROMPTS
from mad.schemas.evidence import EvidenceEntry
from mad.ledger.base import LedgerBackend


def _get_model(agent_id: str) -> str:
    """Get the model for an agent."""
    governance_model = os.environ.get("MAD_GOVERNANCE_MODEL", "gpt-4o-mini")
    default_model = os.environ.get("MAD_DEFAULT_MODEL", "gpt-4o-mini")
    if agent_id in ("verifier", "compliance_risk", "synthesizer"):
        return governance_model
    return default_model


class EnterpriseAgent(BaseAgent):
    """
    Shared execution logic for all enterprise agents.
    
    Uses LangChain ChatOpenAI with structured output for production-grade
    generation, falling back to the direct OpenAI client if LangChain
    is unavailable.
    """

    def core_execute(self, context: dict[str, Any], ledger: LedgerBackend) -> EvidenceEntry:
        """Execute the agent's core specialty using LangChain structured output."""
        try:
            return self._execute_with_langchain(context, ledger)
        except ImportError:
            # Fallback to legacy OpenAI client
            return self._execute_legacy(context, ledger)

    def _execute_with_langchain(self, context: dict[str, Any], ledger: LedgerBackend) -> EvidenceEntry:
        """Production execution path using LangChain."""
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage
        from mad.schemas.enterprise import AgentOutput
        
        model_name = _get_model(self.agent_id)
        llm = ChatOpenAI(model=model_name, temperature=0.2)
        structured_llm = llm.with_structured_output(AgentOutput)
        
        # Build context from ledger
        verified = ledger.get_all(verified_only=True) if ledger else []
        context_parts = [f"## Task Context\n{json.dumps(context, indent=2, default=str)}"]
        
        if verified:
            prior_summaries = []
            for e in verified[-5:]:  # Last 5 entries for context window efficiency
                prior_summaries.append(
                    f"- [{e.author_agent_id}]: {e.content.get('summary', 'No summary')[:200]}"
                )
            context_parts.append(f"\n## Prior Agent Outputs\n" + "\n".join(prior_summaries))
        
        user_prompt = "\n".join(context_parts)
        
        result = structured_llm.invoke([
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_prompt),
        ])
        
        return EvidenceEntry(
            author_agent_id=self.agent_id,
            content=result.model_dump(),
        )

    def _execute_legacy(self, context: dict[str, Any], ledger: LedgerBackend) -> EvidenceEntry:
        """Legacy execution path using direct OpenAI client."""
        user_prompt = f"Context:\n{json.dumps(context, indent=2, default=str)}"
        llm_out = self._execute_llm(user_prompt)
        return EvidenceEntry(
            author_agent_id=self.agent_id,
            content=llm_out,
        )

    def audit(self, entry: EvidenceEntry, ledger: LedgerBackend = None) -> AuditResult:
        """Enterprise agents use LLMs to audit peers."""
        try:
            return self._audit_with_langchain(entry)
        except ImportError:
            audit_out = self._execute_llm_audit(entry.content)
            return AuditResult(
                approved=audit_out.get("approved", True),
                auditor_id=self.agent_id,
                comments=audit_out.get("comments", []),
                rejection_reasons=audit_out.get("rejection_reasons", []),
            )

    def _audit_with_langchain(self, entry: EvidenceEntry) -> AuditResult:
        """Production audit path using LangChain."""
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage
        from mad.schemas.enterprise import AuditOutput
        
        model_name = _get_model(self.agent_id)
        llm = ChatOpenAI(model=model_name, temperature=0.1)
        structured_llm = llm.with_structured_output(AuditOutput)
        
        audit_prompt = (
            f"Audit the following peer entry from [{entry.author_agent_id}] "
            f"for correctness, architectural soundness, and business alignment.\n\n"
            f"Entry content:\n{json.dumps(entry.content, indent=2, default=str)}"
        )
        
        result = structured_llm.invoke([
            SystemMessage(content=f"{self.system_prompt}\n\nYour task now is to AUDIT upstream work."),
            HumanMessage(content=audit_prompt),
        ])
        
        return AuditResult(
            approved=result.approved,
            auditor_id=self.agent_id,
            comments=result.comments,
            rejection_reasons=result.rejection_reasons,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Agent Class Definitions — each with production-grade system prompts
# ═══════════════════════════════════════════════════════════════════════════════

@register_agent("discovery")
class DiscoveryAgent(EnterpriseAgent):
    def __init__(self, **kwargs):
        super().__init__(system_prompt=AGENT_PROMPTS["discovery"], **kwargs)


@register_agent("business_analyst")
class BusinessAnalystAgent(EnterpriseAgent):
    def __init__(self, **kwargs):
        super().__init__(system_prompt=AGENT_PROMPTS["business_analyst"], **kwargs)


@register_agent("solution_deviser")
class SolutionDeviserAgent(EnterpriseAgent):
    def __init__(self, **kwargs):
        super().__init__(system_prompt=AGENT_PROMPTS["solution_deviser"], **kwargs)


@register_agent("technical_architect")
class TechnicalArchitectAgent(EnterpriseAgent):
    def __init__(self, **kwargs):
        super().__init__(system_prompt=AGENT_PROMPTS["technical_architect"], **kwargs)


@register_agent("data_integration")
class DataIntegrationAgent(EnterpriseAgent):
    def __init__(self, **kwargs):
        super().__init__(system_prompt=AGENT_PROMPTS["data_integration"], **kwargs)


@register_agent("builder")
class BuilderAgent(EnterpriseAgent):
    def __init__(self, **kwargs):
        super().__init__(system_prompt=AGENT_PROMPTS["builder"], **kwargs)


@register_agent("test_qa")
class TestQAAgent(EnterpriseAgent):
    def __init__(self, **kwargs):
        super().__init__(system_prompt=AGENT_PROMPTS["test_qa"], **kwargs)


@register_agent("verifier")
class VerifierCriticAgent(EnterpriseAgent):
    def __init__(self, **kwargs):
        super().__init__(system_prompt=AGENT_PROMPTS["verifier"], **kwargs)


@register_agent("business_reviewer")
class BusinessReviewerAgent(EnterpriseAgent):
    def __init__(self, **kwargs):
        super().__init__(system_prompt=AGENT_PROMPTS["business_reviewer"], **kwargs)


@register_agent("compliance_risk")
class ComplianceRiskAgent(EnterpriseAgent):
    def __init__(self, **kwargs):
        super().__init__(system_prompt=AGENT_PROMPTS["compliance_risk"], **kwargs)


@register_agent("synthesizer")
class SynthesizerAgent(EnterpriseAgent):
    def __init__(self, **kwargs):
        super().__init__(system_prompt=AGENT_PROMPTS["synthesizer"], **kwargs)
