from typing import List, Optional, Any
from pydantic import BaseModel, Field

class SharedContext(BaseModel):
    """
    The shared context block injected into every agent prompt.
    Provides strict alignment across the enterprise workflow.
    """
    project_objective: str = Field(description="The primary business goal or problem statement.")
    business_context: str = Field(description="Why this matters to the business and the stakeholders involved.")
    user_personas: List[str] = Field(description="Who is using the system.")
    current_workflow: str = Field(description="How things are done today before this solution.")
    constraints: List[str] = Field(description="Hard constraints (budget, time, compliance).")
    definitions_of_success: List[str] = Field(description="How we measure if this project succeeded.")
    non_goals: List[str] = Field(description="Explicitly what we are NOT building to prevent scope creep.")
    approved_architecture: List[str] = Field(description="Architecture decisions already signed off by the Technical Architect.")
    open_questions: List[str] = Field(description="Unresolved questions that need discovery or design.")
    risk_constraints: List[str] = Field(description="Security, privacy, and operational risks to avoid.")

class AgentOutput(BaseModel):
    """
    The structured output required from every enterprise agent in the workflow.
    """
    summary: str = Field(description="A brief summary of this agent's analysis or contribution.")
    claims: List[str] = Field(description="Specific claims, designs, or requirements proposed by this agent.")
    assumptions: List[str] = Field(description="Assumptions made to arrive at these claims.")
    uncertainties: List[str] = Field(description="Areas where the agent lacks context or confidence.")
    evidence: List[str] = Field(description="Data, best practices, or logic supporting the claims.")
    recommended_next_action: str = Field(description="What the downstream agent should focus on next.")
    blockers: List[str] = Field(default_factory=list, description="If this agent is a Governance role, list reasons why the pipeline must loop back and stop.")

class AuditOutput(BaseModel):
    """
    The structured output required when an agent audits a peer's entry.
    """
    approved: bool = Field(description="True if the entry is accepted, False if it violates architecture or constraints.")
    comments: List[str] = Field(default_factory=list, description="Constructive feedback, analysis, or thoughts regarding the entry, regardless of whether it is approved or rejected.")
    rejection_reasons: List[str] = Field(default_factory=list, description="If rejected, specific reasons why the entry is invalid.")
