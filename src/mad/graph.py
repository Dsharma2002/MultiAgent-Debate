"""
LangGraph Consensus Engine — the core StateGraph that orchestrates all agents.

This module defines:
1. Node functions for each of the 11 agents
2. Conditional edge functions for governance loopback
3. The compiled StateGraph

Each node function:
- Reads relevant fields from the ConsensusState Blackboard
- Builds a focused prompt from the system prompt + Blackboard context
- Invokes the LLM (with or without tools via create_react_agent)
- Emits WebSocket events for the dashboard
- Returns partial state updates
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any
from uuid import uuid4

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent

from mad.agents.prompts import AGENT_PROMPTS
from mad.agents.tools import (
    DISCOVERY_TOOLS,
    SOLUTION_DEVISER_TOOLS,
    TECHNICAL_ARCHITECT_TOOLS,
    VERIFIER_TOOLS,
    COMPLIANCE_TOOLS,
    BUILDER_TOOLS,
    BUSINESS_ANALYST_TOOLS,
)
from mad.events import EventEmitter, EventType, PipelineEvent
from mad.state import (
    ConsensusState,
    DiscoveryOutput,
    AnalysisOutput,
    DesignOutput,
    ArchitectureOutput,
    DataIntegrationOutput,
    BuildOutput,
    TestOutput,
    CritiqueOutput,
    BusinessReviewOutput,
    ComplianceOutput,
    SynthesisOutput,
)

logger = logging.getLogger(__name__)

# Agent metadata for events
AGENT_META = {
    "discovery": {"name": "Discovery Agent", "specialty": "Problem framing, stakeholder analysis, domain research", "step": 0},
    "business_analyst": {"name": "Business Analyst", "specialty": "Requirements engineering, user stories, acceptance criteria", "step": 1},
    "solution_deviser": {"name": "Solution Deviser", "specialty": "Architecture options, tradeoff analysis, technology selection", "step": 2},
    "technical_architect": {"name": "Technical Architect", "specialty": "System design, API contracts, component architecture", "step": 3},
    "data_integration": {"name": "Data & Integration", "specialty": "Data contracts, privacy engineering, external integrations", "step": 4},
    "builder": {"name": "Builder", "specialty": "Implementation planning, sprint breakdown, dependency management", "step": 5},
    "test_qa": {"name": "Test / QA Lead", "specialty": "Test strategy, edge case analysis, quality assurance", "step": 6},
    "verifier": {"name": "Verifier / Critic", "specialty": "Contradiction detection, assumption auditing, gap analysis", "step": 7},
    "business_reviewer": {"name": "Business Reviewer", "specialty": "Business alignment, ROI analysis, market fit", "step": 8},
    "compliance_risk": {"name": "Compliance & Risk", "specialty": "STRIDE threat modeling, regulatory compliance, risk assessment", "step": 9},
    "synthesizer": {"name": "Synthesizer", "specialty": "Consensus synthesis, conflict resolution, executive summary", "step": 10},
}

TOTAL_AGENTS = len(AGENT_META)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _get_model(agent_id: str) -> str:
    """Get the model for an agent. Governance agents use a stronger model."""
    governance_model = os.environ.get("MAD_GOVERNANCE_MODEL", "gpt-4o-mini")
    default_model = os.environ.get("MAD_DEFAULT_MODEL", "gpt-4o-mini")
    
    if agent_id in ("verifier", "compliance_risk", "synthesizer"):
        return governance_model
    return default_model


def _emit(emitter: EventEmitter | None, event_type: EventType, agent_id: str, **kwargs) -> None:
    """Emit a pipeline event with minimum pacing for dashboard animation."""
    if emitter is None:
        return
    
    meta = AGENT_META.get(agent_id, {"name": agent_id, "step": 0})
    
    emitter.emit(PipelineEvent(
        event_type=event_type,
        agent_id=agent_id,
        agent_name=meta["name"],
        step_index=meta["step"],
        data=kwargs.get("data", {}),
    ))
    time.sleep(0.15)


def _get_emitter(config: dict) -> EventEmitter | None:
    """Extract the event emitter from LangGraph config."""
    configurable = config.get("configurable", {})
    return configurable.get("emitter")


def _get_ledger(config: dict):
    """Extract the ledger from LangGraph config."""
    configurable = config.get("configurable", {})
    return configurable.get("ledger")


def _commit_to_ledger(ledger, agent_id: str, content: dict[str, Any]) -> dict[str, Any] | None:
    """Commit an agent's output to the hash-chain ledger."""
    if ledger is None:
        return None
    
    from mad.schemas.evidence import EvidenceEntry
    
    latest = ledger.get_latest()
    prev_hash = latest.entry_hash if latest else "GENESIS"
    
    entry = EvidenceEntry(
        author_agent_id=agent_id,
        content=content,
        verified_status=True,
        prev_hash=prev_hash,
    )
    committed = ledger.append(entry)
    return {
        "entry_id": str(committed.entry_id),
        "entry_hash": committed.entry_hash[:16],
        "prev_hash": committed.prev_hash[:16] if committed.prev_hash != "GENESIS" else "GENESIS",
    }


def _invoke_structured(
    agent_id: str,
    output_model: type,
    context_text: str,
    emitter: EventEmitter | None = None,
    tools: list | None = None,
) -> Any:
    """
    Core LLM invocation pattern used by all agents.
    
    For agents WITH tools: uses create_react_agent for ReAct reasoning,
    then parses the final response into structured output.
    
    For agents WITHOUT tools: uses ChatOpenAI.with_structured_output() directly.
    """
    model_name = _get_model(agent_id)
    prompt = AGENT_PROMPTS[agent_id]
    
    if tools:
        # ReAct agent with tools — let it reason and search, then parse
        llm = ChatOpenAI(model=model_name, temperature=0.2)
        
        react_agent = create_react_agent(
            llm,
            tools=tools,
            prompt=prompt,
        )
        
        # Run the ReAct loop
        result = react_agent.invoke(
            {"messages": [HumanMessage(content=context_text)]}
        )
        
        # Extract the final message content
        final_content = result["messages"][-1].content if result.get("messages") else ""
        
        # Parse into structured output using a second LLM call
        parser_llm = ChatOpenAI(model=model_name, temperature=0.1)
        structured_llm = parser_llm.with_structured_output(output_model)
        
        parsed = structured_llm.invoke([
            SystemMessage(content=(
                "Parse the following analysis into the exact structured format required. "
                "Preserve all details, findings, and scores from the analysis. "
                "Do not add information that wasn't in the analysis."
            )),
            HumanMessage(content=final_content),
        ])
        return parsed
    else:
        # Direct structured generation — simpler, faster, more predictable
        llm = ChatOpenAI(model=model_name, temperature=0.2)
        structured_llm = llm.with_structured_output(output_model)
        
        result = structured_llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content=context_text),
        ])
        return result


def _format_blackboard_section(title: str, content: Any) -> str:
    """Format a Blackboard section for inclusion in an agent's context prompt."""
    if content is None:
        return ""
    if isinstance(content, (list, dict)):
        return f"\n## {title}\n```json\n{json.dumps(content, indent=2, default=str)}\n```\n"
    return f"\n## {title}\n{content}\n"


# ═══════════════════════════════════════════════════════════════════════════════
# Node Functions — one per agent
# ═══════════════════════════════════════════════════════════════════════════════

def discovery_node(state: ConsensusState, config: dict) -> dict:
    """Discovery Agent: transforms raw proposal into structured problem statement."""
    emitter = _get_emitter(config)
    ledger = _get_ledger(config)
    agent_id = "discovery"
    
    _emit(emitter, EventType.AGENT_START, agent_id, data={"specialty": AGENT_META[agent_id]["specialty"]})
    _emit(emitter, EventType.AGENT_THINKING, agent_id)
    
    context = f"## Proposal\n{state.get('proposal_text', '')}"
    
    result = _invoke_structured(agent_id, DiscoveryOutput, context, emitter, tools=DISCOVERY_TOOLS)
    output = result.model_dump()
    
    # Commit to ledger
    ledger_info = _commit_to_ledger(ledger, agent_id, output)
    
    _emit(emitter, EventType.AGENT_PROPOSAL, agent_id, data={
        "content": output, "entry_id": ledger_info.get("entry_id", "") if ledger_info else "",
    })
    _emit(emitter, EventType.GATE_DECISION, agent_id, data={
        "decision": "COMMIT", **(ledger_info or {}),
        "budget_used": ledger.get_total_budget() if ledger else 0,
        "content": output,
    })
    _emit(emitter, EventType.AGENT_COMPLETE, agent_id, data={"success": True})
    
    return {
        "problem_statement": result.problem_statement,
        "stakeholders": result.stakeholders,
        "discovery_research": result.key_findings,
        "domain_context": result.domain_context,
        "current_phase": "discovery",
        "agent_trace": [{"agent_id": agent_id, "output": output, "confidence": result.confidence_score}],
    }


def business_analyst_node(state: ConsensusState, config: dict) -> dict:
    """Business Analyst: converts discovery into structured requirements."""
    emitter = _get_emitter(config)
    ledger = _get_ledger(config)
    agent_id = "business_analyst"
    
    _emit(emitter, EventType.AGENT_START, agent_id, data={"specialty": AGENT_META[agent_id]["specialty"]})
    _emit(emitter, EventType.AGENT_THINKING, agent_id)
    
    context = (
        _format_blackboard_section("Problem Statement", state.get("problem_statement", ""))
        + _format_blackboard_section("Stakeholders", state.get("stakeholders", []))
        + _format_blackboard_section("Domain Context", state.get("domain_context", ""))
        + _format_blackboard_section("Discovery Research", state.get("discovery_research", []))
    )
    
    result = _invoke_structured(agent_id, AnalysisOutput, context, emitter, tools=BUSINESS_ANALYST_TOOLS)
    output = result.model_dump()
    
    ledger_info = _commit_to_ledger(ledger, agent_id, output)
    
    _emit(emitter, EventType.AGENT_PROPOSAL, agent_id, data={
        "content": output, "entry_id": ledger_info.get("entry_id", "") if ledger_info else "",
    })
    _emit(emitter, EventType.GATE_DECISION, agent_id, data={
        "decision": "COMMIT", **(ledger_info or {}),
        "budget_used": ledger.get_total_budget() if ledger else 0,
        "content": output,
    })
    _emit(emitter, EventType.AGENT_COMPLETE, agent_id, data={"success": True})
    
    return {
        "requirements": result.requirements,
        "acceptance_criteria": result.acceptance_criteria,
        "priority_matrix": result.priority_matrix,
        "current_phase": "analysis",
        "agent_trace": [{"agent_id": agent_id, "output": output, "confidence": result.confidence_score}],
    }


def solution_deviser_node(state: ConsensusState, config: dict) -> dict:
    """Solution Deviser: generates architecture options with tradeoff analysis."""
    emitter = _get_emitter(config)
    ledger = _get_ledger(config)
    agent_id = "solution_deviser"
    
    _emit(emitter, EventType.AGENT_START, agent_id, data={"specialty": AGENT_META[agent_id]["specialty"]})
    _emit(emitter, EventType.AGENT_THINKING, agent_id)
    
    # Include governance feedback if this is a revision round
    governance_feedback = ""
    if state.get("critique"):
        governance_feedback = _format_blackboard_section(
            "⚠️ GOVERNANCE FEEDBACK FROM PREVIOUS ROUND — ADDRESS EVERY POINT",
            {
                "verifier_critique": state.get("critique", {}),
                "business_review": state.get("business_review", {}),
                "compliance_assessment": state.get("compliance_assessment", {}),
            }
        )
    
    context = (
        _format_blackboard_section("Problem Statement", state.get("problem_statement", ""))
        + _format_blackboard_section("Requirements", state.get("requirements", []))
        + _format_blackboard_section("Priority Matrix", state.get("priority_matrix", {}))
        + _format_blackboard_section("Stakeholders", state.get("stakeholders", []))
        + governance_feedback
    )
    
    result = _invoke_structured(agent_id, DesignOutput, context, emitter, tools=SOLUTION_DEVISER_TOOLS)
    output = result.model_dump()
    
    ledger_info = _commit_to_ledger(ledger, agent_id, output)
    
    _emit(emitter, EventType.AGENT_PROPOSAL, agent_id, data={
        "content": output, "entry_id": ledger_info.get("entry_id", "") if ledger_info else "",
    })
    _emit(emitter, EventType.GATE_DECISION, agent_id, data={
        "decision": "COMMIT", **(ledger_info or {}),
        "budget_used": ledger.get_total_budget() if ledger else 0,
        "content": output,
    })
    _emit(emitter, EventType.AGENT_COMPLETE, agent_id, data={"success": True})
    
    return {
        "solution_options": result.solution_options,
        "selected_solution": result.recommendation,
        "current_phase": "design",
        "agent_trace": [{"agent_id": agent_id, "output": output, "confidence": result.confidence_score}],
    }


def technical_architect_node(state: ConsensusState, config: dict) -> dict:
    """Technical Architect: designs system architecture from selected solution."""
    emitter = _get_emitter(config)
    ledger = _get_ledger(config)
    agent_id = "technical_architect"
    
    _emit(emitter, EventType.AGENT_START, agent_id, data={"specialty": AGENT_META[agent_id]["specialty"]})
    _emit(emitter, EventType.AGENT_THINKING, agent_id)
    
    context = (
        _format_blackboard_section("Problem Statement", state.get("problem_statement", ""))
        + _format_blackboard_section("Requirements", state.get("requirements", []))
        + _format_blackboard_section("Selected Solution", state.get("selected_solution", ""))
        + _format_blackboard_section("Solution Options", state.get("solution_options", []))
        + _format_blackboard_section("Stakeholders", state.get("stakeholders", []))
    )
    
    result = _invoke_structured(agent_id, ArchitectureOutput, context, emitter, tools=TECHNICAL_ARCHITECT_TOOLS)
    output = result.model_dump()
    
    ledger_info = _commit_to_ledger(ledger, agent_id, output)
    
    _emit(emitter, EventType.AGENT_PROPOSAL, agent_id, data={
        "content": output, "entry_id": ledger_info.get("entry_id", "") if ledger_info else "",
    })
    _emit(emitter, EventType.GATE_DECISION, agent_id, data={
        "decision": "COMMIT", **(ledger_info or {}),
        "budget_used": ledger.get_total_budget() if ledger else 0,
        "content": output,
    })
    _emit(emitter, EventType.AGENT_COMPLETE, agent_id, data={"success": True})
    
    return {
        "architecture_decision": {
            "overview": result.architecture_overview,
            "components": result.components,
            "data_flow": result.data_flow,
            "scalability": result.scalability_strategy,
            "technology_choices": result.technology_choices,
        },
        "system_diagram": result.system_diagram,
        "api_design": result.api_contracts,
        "current_phase": "design",
        "agent_trace": [{"agent_id": agent_id, "output": output, "confidence": result.confidence_score}],
    }


def data_integration_node(state: ConsensusState, config: dict) -> dict:
    """Data & Integration: designs data layer, contracts, and privacy controls."""
    emitter = _get_emitter(config)
    ledger = _get_ledger(config)
    agent_id = "data_integration"
    
    _emit(emitter, EventType.AGENT_START, agent_id, data={"specialty": AGENT_META[agent_id]["specialty"]})
    _emit(emitter, EventType.AGENT_THINKING, agent_id)
    
    context = (
        _format_blackboard_section("Requirements", state.get("requirements", []))
        + _format_blackboard_section("Architecture Decision", state.get("architecture_decision", {}))
        + _format_blackboard_section("API Design", state.get("api_design", []))
        + _format_blackboard_section("Stakeholders", state.get("stakeholders", []))
    )
    
    result = _invoke_structured(agent_id, DataIntegrationOutput, context, emitter)
    output = result.model_dump()
    
    ledger_info = _commit_to_ledger(ledger, agent_id, output)
    
    _emit(emitter, EventType.AGENT_PROPOSAL, agent_id, data={
        "content": output, "entry_id": ledger_info.get("entry_id", "") if ledger_info else "",
    })
    _emit(emitter, EventType.GATE_DECISION, agent_id, data={
        "decision": "COMMIT", **(ledger_info or {}),
        "budget_used": ledger.get_total_budget() if ledger else 0,
        "content": output,
    })
    _emit(emitter, EventType.AGENT_COMPLETE, agent_id, data={"success": True})
    
    return {
        "data_contracts": result.data_contracts,
        "integration_points": result.integration_points,
        "data_privacy_assessment": result.data_privacy_assessment,
        "current_phase": "data",
        "agent_trace": [{"agent_id": agent_id, "output": output, "confidence": result.confidence_score}],
    }


def builder_node(state: ConsensusState, config: dict) -> dict:
    """Builder: creates implementation plan, sprint breakdown, dependency graph."""
    emitter = _get_emitter(config)
    ledger = _get_ledger(config)
    agent_id = "builder"
    
    _emit(emitter, EventType.AGENT_START, agent_id, data={"specialty": AGENT_META[agent_id]["specialty"]})
    _emit(emitter, EventType.AGENT_THINKING, agent_id)
    
    context = (
        _format_blackboard_section("Requirements", state.get("requirements", []))
        + _format_blackboard_section("Architecture Decision", state.get("architecture_decision", {}))
        + _format_blackboard_section("API Design", state.get("api_design", []))
        + _format_blackboard_section("Data Contracts", state.get("data_contracts", []))
        + _format_blackboard_section("Integration Points", state.get("integration_points", []))
    )
    
    result = _invoke_structured(agent_id, BuildOutput, context, emitter, tools=BUILDER_TOOLS)
    output = result.model_dump()
    
    ledger_info = _commit_to_ledger(ledger, agent_id, output)
    
    _emit(emitter, EventType.AGENT_PROPOSAL, agent_id, data={
        "content": output, "entry_id": ledger_info.get("entry_id", "") if ledger_info else "",
    })
    _emit(emitter, EventType.GATE_DECISION, agent_id, data={
        "decision": "COMMIT", **(ledger_info or {}),
        "budget_used": ledger.get_total_budget() if ledger else 0,
        "content": output,
    })
    _emit(emitter, EventType.AGENT_COMPLETE, agent_id, data={"success": True})
    
    return {
        "implementation_plan": result.implementation_plan,
        "sprint_breakdown": result.sprint_breakdown,
        "dependency_graph": result.dependency_graph,
        "current_phase": "build",
        "agent_trace": [{"agent_id": agent_id, "output": output, "confidence": result.confidence_score}],
    }


def test_qa_node(state: ConsensusState, config: dict) -> dict:
    """Test/QA Lead: designs test strategy and generates test cases."""
    emitter = _get_emitter(config)
    ledger = _get_ledger(config)
    agent_id = "test_qa"
    
    _emit(emitter, EventType.AGENT_START, agent_id, data={"specialty": AGENT_META[agent_id]["specialty"]})
    _emit(emitter, EventType.AGENT_THINKING, agent_id)
    
    context = (
        _format_blackboard_section("Requirements", state.get("requirements", []))
        + _format_blackboard_section("Architecture Decision", state.get("architecture_decision", {}))
        + _format_blackboard_section("API Design", state.get("api_design", []))
        + _format_blackboard_section("Data Contracts", state.get("data_contracts", []))
        + _format_blackboard_section("Implementation Plan", state.get("implementation_plan", {}))
    )
    
    result = _invoke_structured(agent_id, TestOutput, context, emitter)
    output = result.model_dump()
    
    ledger_info = _commit_to_ledger(ledger, agent_id, output)
    
    _emit(emitter, EventType.AGENT_PROPOSAL, agent_id, data={
        "content": output, "entry_id": ledger_info.get("entry_id", "") if ledger_info else "",
    })
    _emit(emitter, EventType.GATE_DECISION, agent_id, data={
        "decision": "COMMIT", **(ledger_info or {}),
        "budget_used": ledger.get_total_budget() if ledger else 0,
        "content": output,
    })
    _emit(emitter, EventType.AGENT_COMPLETE, agent_id, data={"success": True})
    
    return {
        "test_strategy": result.test_strategy,
        "test_cases": result.test_cases,
        "coverage_analysis": result.coverage_analysis,
        "current_phase": "qa",
        "agent_trace": [{"agent_id": agent_id, "output": output, "confidence": result.confidence_score}],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Governance Nodes — Adversarial Challenge Phase
# ═══════════════════════════════════════════════════════════════════════════════

def verifier_node(state: ConsensusState, config: dict) -> dict:
    """Verifier/Critic: adversarial analysis — finds contradictions and gaps."""
    emitter = _get_emitter(config)
    ledger = _get_ledger(config)
    agent_id = "verifier"
    
    _emit(emitter, EventType.AGENT_START, agent_id, data={"specialty": AGENT_META[agent_id]["specialty"]})
    _emit(emitter, EventType.AGENT_THINKING, agent_id)
    
    # The Verifier sees the ENTIRE Blackboard
    context = (
        _format_blackboard_section("Problem Statement", state.get("problem_statement", ""))
        + _format_blackboard_section("Requirements", state.get("requirements", []))
        + _format_blackboard_section("Solution Options", state.get("solution_options", []))
        + _format_blackboard_section("Selected Solution", state.get("selected_solution", ""))
        + _format_blackboard_section("Architecture Decision", state.get("architecture_decision", {}))
        + _format_blackboard_section("API Design", state.get("api_design", []))
        + _format_blackboard_section("Data Contracts", state.get("data_contracts", []))
        + _format_blackboard_section("Implementation Plan", state.get("implementation_plan", {}))
        + _format_blackboard_section("Test Strategy", state.get("test_strategy", {}))
        + _format_blackboard_section("Test Cases", state.get("test_cases", []))
    )
    
    result = _invoke_structured(agent_id, CritiqueOutput, context, emitter, tools=VERIFIER_TOOLS)
    output = result.model_dump()
    
    ledger_info = _commit_to_ledger(ledger, agent_id, output)
    
    # Emit as objection or support depending on findings
    has_blockers = len(result.blockers) > 0
    event_type = EventType.AGENT_OBJECTION if has_blockers else EventType.AGENT_SUPPORT
    
    _emit(emitter, event_type, agent_id, data={
        "content": output,
        "approved": not has_blockers,
        "reasons": result.blockers if has_blockers else ["Analysis passes verification checks."],
        "target_agent": "pipeline",
    })
    _emit(emitter, EventType.GATE_DECISION, agent_id, data={
        "decision": "COMMIT", **(ledger_info or {}),
        "budget_used": ledger.get_total_budget() if ledger else 0,
        "content": output,
    })
    _emit(emitter, EventType.AGENT_COMPLETE, agent_id, data={"success": True})
    
    return {
        "critique": output,
        "debate_history": [{"agent_id": agent_id, "type": "critique", "blockers": result.blockers, "assessment": result.overall_assessment}],
        "current_phase": "governance",
        "agent_trace": [{"agent_id": agent_id, "output": output, "confidence": result.confidence_score}],
    }


def business_reviewer_node(state: ConsensusState, config: dict) -> dict:
    """Business Reviewer: evaluates business alignment and ROI."""
    emitter = _get_emitter(config)
    ledger = _get_ledger(config)
    agent_id = "business_reviewer"
    
    _emit(emitter, EventType.AGENT_START, agent_id, data={"specialty": AGENT_META[agent_id]["specialty"]})
    _emit(emitter, EventType.AGENT_THINKING, agent_id)
    
    context = (
        _format_blackboard_section("Problem Statement", state.get("problem_statement", ""))
        + _format_blackboard_section("Stakeholders", state.get("stakeholders", []))
        + _format_blackboard_section("Requirements", state.get("requirements", []))
        + _format_blackboard_section("Solution Options", state.get("solution_options", []))
        + _format_blackboard_section("Selected Solution", state.get("selected_solution", ""))
        + _format_blackboard_section("Architecture Decision", state.get("architecture_decision", {}))
        + _format_blackboard_section("Implementation Plan", state.get("implementation_plan", {}))
        + _format_blackboard_section("Sprint Breakdown", state.get("sprint_breakdown", []))
    )
    
    result = _invoke_structured(agent_id, BusinessReviewOutput, context, emitter)
    output = result.model_dump()
    
    ledger_info = _commit_to_ledger(ledger, agent_id, output)
    
    has_blockers = len(result.blockers) > 0
    event_type = EventType.AGENT_OBJECTION if has_blockers else EventType.AGENT_SUPPORT
    
    _emit(emitter, event_type, agent_id, data={
        "content": output,
        "approved": not has_blockers,
        "reasons": result.blockers if has_blockers else [f"Business alignment score: {result.business_alignment_score}"],
        "target_agent": "pipeline",
    })
    _emit(emitter, EventType.GATE_DECISION, agent_id, data={
        "decision": "COMMIT", **(ledger_info or {}),
        "budget_used": ledger.get_total_budget() if ledger else 0,
        "content": output,
    })
    _emit(emitter, EventType.AGENT_COMPLETE, agent_id, data={"success": True})
    
    return {
        "business_review": output,
        "debate_history": [{"agent_id": agent_id, "type": "business_review", "blockers": result.blockers, "recommendation": result.recommendation}],
        "risk_register": [{"source": "business_reviewer", "risks": result.business_risks}],
        "current_phase": "governance",
        "agent_trace": [{"agent_id": agent_id, "output": output, "confidence": result.confidence_score}],
    }


def compliance_risk_node(state: ConsensusState, config: dict) -> dict:
    """Compliance & Risk: STRIDE threat model and regulatory assessment."""
    emitter = _get_emitter(config)
    ledger = _get_ledger(config)
    agent_id = "compliance_risk"
    
    _emit(emitter, EventType.AGENT_START, agent_id, data={"specialty": AGENT_META[agent_id]["specialty"]})
    _emit(emitter, EventType.AGENT_THINKING, agent_id)
    
    context = (
        _format_blackboard_section("Problem Statement", state.get("problem_statement", ""))
        + _format_blackboard_section("Architecture Decision", state.get("architecture_decision", {}))
        + _format_blackboard_section("API Design", state.get("api_design", []))
        + _format_blackboard_section("Data Contracts", state.get("data_contracts", []))
        + _format_blackboard_section("Data Privacy Assessment", state.get("data_privacy_assessment", {}))
        + _format_blackboard_section("Implementation Plan", state.get("implementation_plan", {}))
        + _format_blackboard_section("Test Strategy", state.get("test_strategy", {}))
    )
    
    result = _invoke_structured(agent_id, ComplianceOutput, context, emitter, tools=COMPLIANCE_TOOLS)
    output = result.model_dump()
    
    ledger_info = _commit_to_ledger(ledger, agent_id, output)
    
    has_blockers = len(result.blockers) > 0
    event_type = EventType.AGENT_OBJECTION if has_blockers else EventType.AGENT_SUPPORT
    
    _emit(emitter, event_type, agent_id, data={
        "content": output,
        "approved": not has_blockers,
        "reasons": result.blockers if has_blockers else [f"Overall risk rating: {result.overall_risk_rating}"],
        "target_agent": "pipeline",
    })
    _emit(emitter, EventType.GATE_DECISION, agent_id, data={
        "decision": "COMMIT", **(ledger_info or {}),
        "budget_used": ledger.get_total_budget() if ledger else 0,
        "content": output,
    })
    _emit(emitter, EventType.AGENT_COMPLETE, agent_id, data={"success": True})
    
    return {
        "compliance_assessment": output,
        "risk_register": [{"source": "compliance_risk", "risks": result.risk_register}],
        "debate_history": [{"agent_id": agent_id, "type": "compliance", "blockers": result.blockers, "risk_rating": result.overall_risk_rating}],
        "current_phase": "governance",
        "agent_trace": [{"agent_id": agent_id, "output": output, "confidence": result.confidence_score}],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Synthesis Node
# ═══════════════════════════════════════════════════════════════════════════════

def synthesizer_node(state: ConsensusState, config: dict) -> dict:
    """Synthesizer: merges all outputs into final consensus verdict."""
    emitter = _get_emitter(config)
    ledger = _get_ledger(config)
    agent_id = "synthesizer"
    
    _emit(emitter, EventType.AGENT_START, agent_id, data={"specialty": AGENT_META[agent_id]["specialty"]})
    _emit(emitter, EventType.AGENT_THINKING, agent_id)
    
    # Synthesizer sees EVERYTHING
    context = (
        _format_blackboard_section("Problem Statement", state.get("problem_statement", ""))
        + _format_blackboard_section("Stakeholders", state.get("stakeholders", []))
        + _format_blackboard_section("Requirements", state.get("requirements", []))
        + _format_blackboard_section("Solution Options", state.get("solution_options", []))
        + _format_blackboard_section("Selected Solution", state.get("selected_solution", ""))
        + _format_blackboard_section("Architecture Decision", state.get("architecture_decision", {}))
        + _format_blackboard_section("Implementation Plan", state.get("implementation_plan", {}))
        + _format_blackboard_section("Test Strategy", state.get("test_strategy", {}))
        + _format_blackboard_section("Verifier Critique", state.get("critique", {}))
        + _format_blackboard_section("Business Review", state.get("business_review", {}))
        + _format_blackboard_section("Compliance Assessment", state.get("compliance_assessment", {}))
        + _format_blackboard_section("Risk Register", state.get("risk_register", []))
        + _format_blackboard_section("Debate History", state.get("debate_history", []))
        + f"\n## Iteration Count: {state.get('iteration_count', 0)}"
    )
    
    result = _invoke_structured(agent_id, SynthesisOutput, context, emitter)
    output = result.model_dump()
    
    ledger_info = _commit_to_ledger(ledger, agent_id, output)
    
    _emit(emitter, EventType.JUDGE_SYNTHESIS, agent_id, data={
        "content": output, "entry_id": ledger_info.get("entry_id", "") if ledger_info else "",
        "consensus_score": result.consensus_score,
        "verdict": result.verdict,
    })
    _emit(emitter, EventType.GATE_DECISION, agent_id, data={
        "decision": "COMMIT", **(ledger_info or {}),
        "budget_used": ledger.get_total_budget() if ledger else 0,
        "content": output,
    })
    _emit(emitter, EventType.AGENT_COMPLETE, agent_id, data={"success": True})
    
    return {
        "final_synthesis": output,
        "consensus_score": result.consensus_score,
        "current_phase": "synthesis",
        "agent_trace": [{"agent_id": agent_id, "output": output}],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Conditional Edge — Governance Loopback
# ═══════════════════════════════════════════════════════════════════════════════

MAX_ITERATIONS = 2

def should_loop_back(state: ConsensusState) -> str:
    """
    Decide whether to loop back to Solution Deviser or proceed to Synthesis.
    
    Loops back if:
    - Any governance agent raised blockers AND
    - We haven't exceeded MAX_ITERATIONS
    
    Otherwise proceeds to synthesis.
    """
    iteration = state.get("iteration_count", 0)
    
    if iteration >= MAX_ITERATIONS:
        logger.warning(f"[Governance] Max iterations ({MAX_ITERATIONS}) reached. Forcing synthesis.")
        return "synthesizer"
    
    # Check for blockers from governance agents
    critique = state.get("critique", {})
    business_review = state.get("business_review", {})
    compliance = state.get("compliance_assessment", {})
    
    verifier_blockers = critique.get("blockers", []) if isinstance(critique, dict) else []
    business_blockers = business_review.get("blockers", []) if isinstance(business_review, dict) else []
    compliance_blockers = compliance.get("blockers", []) if isinstance(compliance, dict) else []
    
    all_blockers = verifier_blockers + business_blockers + compliance_blockers
    
    if all_blockers:
        logger.warning(f"[Governance] {len(all_blockers)} blocker(s) found. Looping back to Solution Deviser.")
        return "solution_deviser"
    
    return "synthesizer"


def _increment_iteration(state: ConsensusState) -> dict:
    """Passthrough node that increments the iteration counter before loopback."""
    return {"iteration_count": state.get("iteration_count", 0) + 1}


# ═══════════════════════════════════════════════════════════════════════════════
# Graph Builder
# ═══════════════════════════════════════════════════════════════════════════════

def build_consensus_graph():
    """
    Build and compile the LangGraph StateGraph for the consensus engine.
    
    Graph topology:
    
    START → discovery → business_analyst → solution_deviser → technical_architect →
    data_integration → builder → test_qa → verifier → business_reviewer →
    compliance_risk → [should_loop_back?]
        YES → increment_iteration → solution_deviser (loop)
        NO  → synthesizer → END
    """
    graph = StateGraph(ConsensusState)
    
    # ── Add all agent nodes ──────────────────────────────────────────────
    graph.add_node("discovery", discovery_node)
    graph.add_node("business_analyst", business_analyst_node)
    graph.add_node("solution_deviser", solution_deviser_node)
    graph.add_node("technical_architect", technical_architect_node)
    graph.add_node("data_integration", data_integration_node)
    graph.add_node("builder", builder_node)
    graph.add_node("test_qa", test_qa_node)
    graph.add_node("verifier", verifier_node)
    graph.add_node("business_reviewer", business_reviewer_node)
    graph.add_node("compliance_risk", compliance_risk_node)
    graph.add_node("increment_iteration", _increment_iteration)
    graph.add_node("synthesizer", synthesizer_node)
    
    # ── Add edges (sequential pipeline) ──────────────────────────────────
    graph.add_edge(START, "discovery")
    graph.add_edge("discovery", "business_analyst")
    graph.add_edge("business_analyst", "solution_deviser")
    graph.add_edge("solution_deviser", "technical_architect")
    graph.add_edge("technical_architect", "data_integration")
    graph.add_edge("data_integration", "builder")
    graph.add_edge("builder", "test_qa")
    graph.add_edge("test_qa", "verifier")
    graph.add_edge("verifier", "business_reviewer")
    graph.add_edge("business_reviewer", "compliance_risk")
    
    # ── Conditional governance loopback ──────────────────────────────────
    graph.add_conditional_edges(
        "compliance_risk",
        should_loop_back,
        {
            "solution_deviser": "increment_iteration",
            "synthesizer": "synthesizer",
        },
    )
    graph.add_edge("increment_iteration", "solution_deviser")
    
    # ── Terminal ─────────────────────────────────────────────────────────
    graph.add_edge("synthesizer", END)
    
    return graph.compile()
