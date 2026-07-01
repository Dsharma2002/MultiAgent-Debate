"""
Consensus State — the Blackboard shared across all agents in the LangGraph pipeline.

Every agent reads specific fields from this state and writes back its outputs.
This eliminates copy-paste context sharing — each agent sees exactly what it needs
from the structured Blackboard, and downstream agents automatically inherit
upstream decisions.

LangGraph TypedDict with Annotated reducers for accumulating fields.
"""

from __future__ import annotations

import operator
from typing import Any, Annotated

from typing_extensions import TypedDict
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# LangGraph State — The Blackboard
# ═══════════════════════════════════════════════════════════════════════════════

class ConsensusState(TypedDict, total=False):
    """
    The shared Blackboard state that flows through the LangGraph pipeline.

    Fields are organized by the agent that writes them. Each agent reads
    upstream fields and writes its own section. Annotated list fields use
    operator.add to accumulate entries across nodes.
    """

    # ─── Input (set once at pipeline start) ──────────────────────────────
    proposal_text: str
    proposal_id: str

    # ─── Discovery Phase ─────────────────────────────────────────────────
    problem_statement: str
    stakeholders: list[str]
    discovery_research: list[str]
    domain_context: str

    # ─── Analysis Phase ──────────────────────────────────────────────────
    requirements: list[dict[str, Any]]
    acceptance_criteria: list[str]
    priority_matrix: dict[str, Any]

    # ─── Design Phase ────────────────────────────────────────────────────
    solution_options: list[dict[str, Any]]
    selected_solution: str
    architecture_decision: dict[str, Any]
    system_diagram: str
    api_design: list[dict[str, Any]]

    # ─── Data & Integration ──────────────────────────────────────────────
    data_contracts: list[dict[str, Any]]
    integration_points: list[dict[str, Any]]
    data_privacy_assessment: dict[str, Any]

    # ─── Build Phase ─────────────────────────────────────────────────────
    implementation_plan: dict[str, Any]
    sprint_breakdown: list[dict[str, Any]]
    dependency_graph: dict[str, Any]

    # ─── QA Phase ────────────────────────────────────────────────────────
    test_strategy: dict[str, Any]
    test_cases: list[dict[str, Any]]
    coverage_analysis: dict[str, Any]

    # ─── Governance / Debate (accumulate across rounds) ──────────────────
    critique: dict[str, Any]
    business_review: dict[str, Any]
    compliance_assessment: dict[str, Any]
    risk_register: Annotated[list[dict[str, Any]], operator.add]
    debate_history: Annotated[list[dict[str, Any]], operator.add]

    # ─── Consensus ───────────────────────────────────────────────────────
    consensus_score: float
    final_synthesis: dict[str, Any]

    # ─── Control Flow ────────────────────────────────────────────────────
    current_phase: str
    iteration_count: int

    # ─── Trace (accumulates every agent's output for the ledger) ─────────
    agent_trace: Annotated[list[dict[str, Any]], operator.add]


# ═══════════════════════════════════════════════════════════════════════════════
# Pydantic Output Models — Structured output for each agent
# ═══════════════════════════════════════════════════════════════════════════════

class DiscoveryOutput(BaseModel):
    """Structured output from the Discovery agent."""
    problem_statement: str = Field(
        description="A single, precise paragraph framing the core problem. "
        "Specific enough that two independent teams could build similar solutions from it."
    )
    stakeholders: list[str] = Field(
        description="Complete list of stakeholder groups with their roles and incentives."
    )
    key_findings: list[str] = Field(
        description="Numbered research findings about the problem domain, market landscape, "
        "and competitive context."
    )
    domain_context: str = Field(
        description="Industry landscape, competitive dynamics, regulatory environment, "
        "and technology trends relevant to this proposal."
    )
    assumptions: list[str] = Field(
        description="Explicit working assumptions that downstream agents must validate or challenge."
    )
    open_questions: list[str] = Field(
        description="Unresolved items requiring further investigation."
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description="Self-assessed confidence in this analysis (0.0-1.0)."
    )


class AnalysisOutput(BaseModel):
    """Structured output from the Business Analyst agent."""
    requirements: list[dict[str, Any]] = Field(
        description="Structured requirements, each with id, title, description, "
        "priority (P0-P3), type (functional/non-functional), and acceptance_criteria."
    )
    user_stories: list[str] = Field(
        description="User stories in 'As a [role], I want [feature] so that [benefit]' format."
    )
    acceptance_criteria: list[str] = Field(
        description="Measurable acceptance criteria for the overall solution."
    )
    priority_matrix: dict[str, Any] = Field(
        description="MoSCoW prioritization: must_have, should_have, could_have, wont_have lists."
    )
    effort_estimate: str = Field(
        description="High-level effort estimate with justification."
    )
    risks_identified: list[str] = Field(
        description="Business risks identified during analysis."
    )
    confidence_score: float = Field(ge=0.0, le=1.0)


class DesignOutput(BaseModel):
    """Structured output from the Solution Deviser agent."""
    solution_options: list[dict[str, Any]] = Field(
        description="2-3 solution options, each with name, description, pros, cons, "
        "estimated_cost, time_to_market, and technical_complexity (low/medium/high)."
    )
    recommendation: str = Field(
        description="Which option is recommended and a detailed justification."
    )
    tradeoff_analysis: str = Field(
        description="Comparative analysis of the options across dimensions: "
        "cost, speed, scalability, maintainability, risk."
    )
    assumptions: list[str] = Field(
        description="Design assumptions that the Technical Architect must validate."
    )
    confidence_score: float = Field(ge=0.0, le=1.0)


class ArchitectureOutput(BaseModel):
    """Structured output from the Technical Architect agent."""
    architecture_overview: str = Field(
        description="High-level architecture description."
    )
    components: list[dict[str, Any]] = Field(
        description="System components with name, responsibility, technology_stack, "
        "and interfaces."
    )
    system_diagram: str = Field(
        description="Mermaid diagram syntax for the system architecture."
    )
    api_contracts: list[dict[str, Any]] = Field(
        description="API endpoints with method, path, request_schema, response_schema."
    )
    data_flow: str = Field(
        description="Description of how data flows through the system."
    )
    scalability_strategy: str = Field(
        description="How the system scales under load."
    )
    technology_choices: list[dict[str, Any]] = Field(
        description="Technology selections with justification."
    )
    confidence_score: float = Field(ge=0.0, le=1.0)


class DataIntegrationOutput(BaseModel):
    """Structured output from the Data/Integration agent."""
    data_contracts: list[dict[str, Any]] = Field(
        description="Data schemas and contracts between components."
    )
    integration_points: list[dict[str, Any]] = Field(
        description="External system integrations with protocol, auth, rate_limits."
    )
    data_privacy_assessment: dict[str, Any] = Field(
        description="Privacy impact: data_classification, pii_fields, retention_policy, "
        "compliance_requirements."
    )
    migration_plan: str = Field(
        description="Data migration strategy if applicable."
    )
    data_quality_checks: list[str] = Field(
        description="Data quality validation rules."
    )
    confidence_score: float = Field(ge=0.0, le=1.0)


class BuildOutput(BaseModel):
    """Structured output from the Builder agent."""
    implementation_plan: dict[str, Any] = Field(
        description="Phased implementation plan with milestones, deliverables, and timelines."
    )
    sprint_breakdown: list[dict[str, Any]] = Field(
        description="Sprint-level breakdown with sprint_number, goal, tasks, dependencies."
    )
    dependency_graph: dict[str, Any] = Field(
        description="Module dependency graph: which modules must be built first."
    )
    code_structure: str = Field(
        description="Proposed directory/module structure."
    )
    technical_debt_items: list[str] = Field(
        description="Known technical debt that will be accepted in v1."
    )
    confidence_score: float = Field(ge=0.0, le=1.0)


class TestOutput(BaseModel):
    """Structured output from the Test/QA agent."""
    test_strategy: dict[str, Any] = Field(
        description="Testing strategy: unit_test_coverage_target, integration_strategy, "
        "e2e_approach, performance_benchmarks."
    )
    test_cases: list[dict[str, Any]] = Field(
        description="Test cases with id, description, type (unit/integration/e2e), "
        "priority, expected_result, edge_cases."
    )
    coverage_analysis: dict[str, Any] = Field(
        description="Coverage analysis: critical_paths, risk_areas, untestable_components."
    )
    qa_risks: list[str] = Field(
        description="Quality risks and mitigation strategies."
    )
    confidence_score: float = Field(ge=0.0, le=1.0)


class CritiqueOutput(BaseModel):
    """Structured output from the Verifier/Critic agent."""
    contradictions_found: list[dict[str, Any]] = Field(
        description="Contradictions between agent outputs: agent_a, claim_a, "
        "agent_b, claim_b, nature_of_contradiction."
    )
    assumption_challenges: list[dict[str, Any]] = Field(
        description="Challenged assumptions: original_assumption, challenge, "
        "evidence_against, severity (critical/major/minor)."
    )
    gaps_identified: list[str] = Field(
        description="Missing pieces in the overall proposal."
    )
    blockers: list[str] = Field(
        default_factory=list,
        description="Critical issues that MUST be resolved before proceeding. "
        "Empty list means no blockers."
    )
    overall_assessment: str = Field(
        description="Overall verdict: APPROVE, CONDITIONAL_APPROVE, or REJECT "
        "with detailed reasoning."
    )
    confidence_score: float = Field(ge=0.0, le=1.0)


class BusinessReviewOutput(BaseModel):
    """Structured output from the Business Reviewer agent."""
    business_alignment_score: float = Field(
        ge=0.0, le=1.0,
        description="How well the solution aligns with stated business objectives (0-1)."
    )
    roi_assessment: str = Field(
        description="Return on investment analysis."
    )
    market_fit_analysis: str = Field(
        description="Product-market fit assessment."
    )
    business_risks: list[dict[str, Any]] = Field(
        description="Business risks with description, likelihood, impact, mitigation."
    )
    blockers: list[str] = Field(
        default_factory=list,
        description="Business-critical issues that block proceeding."
    )
    recommendation: str = Field(
        description="PROCEED, REVISE, or REJECT with reasoning."
    )
    confidence_score: float = Field(ge=0.0, le=1.0)


class ComplianceOutput(BaseModel):
    """Structured output from the Compliance/Risk agent."""
    regulatory_requirements: list[str] = Field(
        description="Applicable regulations (GDPR, SOC2, HIPAA, PCI-DSS, etc.)."
    )
    compliance_gaps: list[dict[str, Any]] = Field(
        description="Compliance gaps with regulation, gap_description, severity, remediation."
    )
    threat_model: dict[str, Any] = Field(
        description="STRIDE threat model: spoofing, tampering, repudiation, "
        "information_disclosure, denial_of_service, elevation_of_privilege."
    )
    risk_register: list[dict[str, Any]] = Field(
        description="Risk register entries with risk_id, description, likelihood, "
        "impact, risk_score, mitigation_strategy."
    )
    blockers: list[str] = Field(
        default_factory=list,
        description="Compliance violations that MUST be resolved."
    )
    overall_risk_rating: str = Field(
        description="LOW, MEDIUM, HIGH, or CRITICAL with justification."
    )
    confidence_score: float = Field(ge=0.0, le=1.0)


class SynthesisOutput(BaseModel):
    """Structured output from the Synthesizer/Program Lead agent."""
    executive_summary: str = Field(
        description="3-5 sentence executive summary of the entire proposal."
    )
    consensus_score: float = Field(
        ge=0.0, le=1.0,
        description="Aggregated consensus score across all agents (0-1)."
    )
    resolved_disagreements: list[str] = Field(
        description="How each disagreement between agents was resolved."
    )
    final_recommendations: list[str] = Field(
        description="Prioritized list of final recommendations."
    )
    implementation_roadmap: str = Field(
        description="Concise implementation roadmap with phases and milestones."
    )
    risk_summary: str = Field(
        description="Top 3 risks and their mitigations."
    )
    verdict: str = Field(
        description="APPROVED, CONDITIONALLY_APPROVED, or REJECTED with reasoning."
    )
    next_steps: list[str] = Field(
        description="Concrete next steps for the team."
    )
