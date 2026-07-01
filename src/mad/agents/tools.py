"""
Agent Tools — Domain-specific tools for the Multi-Agent Consensus Engine.

Tools are @tool-decorated functions that agents can invoke during their
reasoning process. They provide capabilities the LLM doesn't have natively:
- Web search for current information
- Structured analysis frameworks
- Deterministic calculations

Tools gracefully degrade if API keys are missing.
"""

from __future__ import annotations

import os
import json
import math
from typing import Any

from langchain_core.tools import tool


# ═══════════════════════════════════════════════════════════════════════════════
# Research Tools
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def web_search(query: str) -> str:
    """Search the web for current information about a topic. Use this to research
    market trends, competitive landscape, technology comparisons, regulatory
    requirements, or any domain-specific context that benefits from real-time data.
    
    Args:
        query: A specific, well-formed search query. Be precise — 
               "GDPR data retention requirements for SaaS" is better than "GDPR rules".
    """
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not tavily_key:
        return (
            "[Web search unavailable — no TAVILY_API_KEY configured. "
            "Reason from your training knowledge instead. Be explicit about "
            "any claims that would benefit from verification.]"
        )
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=tavily_key)
        results = client.search(query, max_results=5, search_depth="advanced")
        
        formatted = []
        for r in results.get("results", []):
            formatted.append(
                f"**{r.get('title', 'Untitled')}**\n"
                f"Source: {r.get('url', 'N/A')}\n"
                f"{r.get('content', 'No content')}\n"
            )
        
        return "\n---\n".join(formatted) if formatted else "No results found."
    except Exception as e:
        return f"[Web search failed: {e}. Reason from training knowledge instead.]"


# ═══════════════════════════════════════════════════════════════════════════════
# Risk & Compliance Tools
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def calculate_risk_score(
    likelihood: int,
    impact: int,
    description: str,
) -> str:
    """Calculate a quantified risk score using the standard risk matrix.
    
    Args:
        likelihood: Probability of occurrence (1=Rare, 2=Unlikely, 3=Possible, 4=Likely, 5=Almost Certain)
        impact: Business impact if realized (1=Negligible, 2=Minor, 3=Moderate, 4=Major, 5=Catastrophic)
        description: Brief description of the risk being assessed.
    """
    likelihood = max(1, min(5, likelihood))
    impact = max(1, min(5, impact))
    
    score = likelihood * impact
    
    if score >= 20:
        rating = "CRITICAL"
        action = "Immediate mitigation required. Must be resolved before proceeding."
    elif score >= 15:
        rating = "HIGH"
        action = "Mitigation plan required in the current phase."
    elif score >= 8:
        rating = "MEDIUM"
        action = "Monitor and mitigate in the implementation plan."
    elif score >= 4:
        rating = "LOW"
        action = "Accept with documented rationale."
    else:
        rating = "NEGLIGIBLE"
        action = "No action required."

    return (
        f"Risk Assessment: {description}\n"
        f"  Likelihood: {likelihood}/5 | Impact: {impact}/5\n"
        f"  Risk Score: {score}/25 → {rating}\n"
        f"  Recommended Action: {action}"
    )


@tool
def run_stride_analysis(component_name: str, component_description: str) -> str:
    """Run a STRIDE threat model analysis on a system component.
    Produces a structured threat analysis across all six STRIDE categories.
    
    Args:
        component_name: Name of the component being analyzed.
        component_description: What the component does, what data it handles, 
                              and how it interfaces with other components.
    """
    return (
        f"STRIDE Threat Model for: {component_name}\n"
        f"Component: {component_description}\n\n"
        f"Analyze each threat category:\n"
        f"  [S] Spoofing: Can an attacker impersonate a legitimate user/service of {component_name}?\n"
        f"  [T] Tampering: Can data handled by {component_name} be modified without detection?\n"
        f"  [R] Repudiation: Can actions performed through {component_name} be denied?\n"
        f"  [I] Information Disclosure: Can {component_name} leak sensitive data?\n"
        f"  [D] Denial of Service: Can {component_name} be overwhelmed or shut down?\n"
        f"  [E] Elevation of Privilege: Can a user gain unauthorized access via {component_name}?\n\n"
        f"For each applicable threat, assess likelihood (1-5) and impact (1-5), "
        f"and propose a specific mitigation."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Analysis & Validation Tools
# ═══════════════════════════════════════════════════════════════════════════════

@tool
def validate_requirements_completeness(requirements_json: str) -> str:
    """Validate a set of requirements against SMART criteria and check for 
    completeness. Identifies requirements that are vague, untestable, or missing
    key attributes.
    
    Args:
        requirements_json: JSON string of requirements list, each with 
                          id, title, description, priority, acceptance_criteria.
    """
    try:
        requirements = json.loads(requirements_json)
    except json.JSONDecodeError:
        return "Error: Could not parse requirements JSON. Ensure it's valid JSON."
    
    issues = []
    for i, req in enumerate(requirements):
        req_id = req.get("id", f"REQ-{i+1}")
        
        # Check for required fields
        for field in ["title", "description", "priority"]:
            if not req.get(field):
                issues.append(f"  {req_id}: Missing '{field}' field")
        
        # Check acceptance criteria
        ac = req.get("acceptance_criteria", "")
        if not ac:
            issues.append(f"  {req_id}: No acceptance criteria defined (CRITICAL)")
        elif len(str(ac)) < 20:
            issues.append(f"  {req_id}: Acceptance criteria too vague — needs measurable targets")
        
        # Check for vague language
        vague_terms = ["should", "might", "could", "nice to have", "fast", "good", "user-friendly"]
        desc = str(req.get("description", "")).lower()
        found_vague = [t for t in vague_terms if t in desc]
        if found_vague:
            issues.append(f"  {req_id}: Contains vague language: {found_vague} — quantify instead")
    
    if issues:
        return (
            f"Requirements Validation: {len(issues)} issue(s) found in {len(requirements)} requirements:\n"
            + "\n".join(issues)
        )
    return f"Requirements Validation: All {len(requirements)} requirements pass completeness checks."


@tool
def compare_solutions(options_json: str) -> str:
    """Generate a structured comparison matrix for solution options.
    Evaluates each option across standardized dimensions.
    
    Args:
        options_json: JSON string with a list of solution options, 
                     each having name, description, pros, cons, estimated_cost.
    """
    try:
        options = json.loads(options_json)
    except json.JSONDecodeError:
        return "Error: Could not parse options JSON."
    
    dimensions = [
        "Technical Feasibility", "Scalability", "Time to Market",
        "Total Cost of Ownership", "Risk Profile", "Maintainability",
        "Team Familiarity", "Community/Support",
    ]
    
    header = "| Dimension | " + " | ".join(o.get("name", f"Option {i+1}") for i, o in enumerate(options)) + " |"
    separator = "|" + "|".join(["---"] * (len(options) + 1)) + "|"
    
    rows = [header, separator]
    for dim in dimensions:
        row = f"| {dim} | " + " | ".join(["[Score 1-5]"] * len(options)) + " |"
        rows.append(row)
    
    return (
        "Solution Comparison Matrix\n"
        "(Fill in scores 1-5 for each dimension based on your analysis)\n\n"
        + "\n".join(rows)
        + "\n\nTotal each column and recommend the option with the highest weighted score."
    )


@tool
def find_contradictions(agent_outputs_json: str) -> str:
    """Systematically cross-reference multiple agents' outputs to find 
    contradictions, gaps, and inconsistencies.
    
    Args:
        agent_outputs_json: JSON string with a dict mapping agent_id to their 
                           output summary (key claims and decisions).
    """
    try:
        outputs = json.loads(agent_outputs_json)
    except json.JSONDecodeError:
        return "Error: Could not parse agent outputs JSON."
    
    agents = list(outputs.keys())
    check_pairs = []
    for i, a in enumerate(agents):
        for b in agents[i+1:]:
            check_pairs.append((a, b))
    
    return (
        f"Contradiction Analysis Framework\n"
        f"Analyzing {len(agents)} agents across {len(check_pairs)} pairs:\n\n"
        f"For each pair, check:\n"
        + "\n".join(
            f"  [{a}] vs [{b}]: Compare claims, assumptions, and technical decisions. "
            f"Flag any statement in [{a}] that contradicts a statement in [{b}]."
            for a, b in check_pairs
        )
        + "\n\nAlso check for GAPS: Requirements without architecture? "
        "Architecture without tests? Risks without mitigations?"
    )


@tool
def estimate_effort(task_description: str, complexity: str) -> str:
    """Estimate engineering effort for a task using calibrated estimation.
    
    Args:
        task_description: What needs to be built.
        complexity: One of 'trivial', 'simple', 'moderate', 'complex', 'very_complex'.
    """
    effort_map = {
        "trivial": {"days": "0.5-1", "engineers": 1, "risk": "LOW"},
        "simple": {"days": "1-3", "engineers": 1, "risk": "LOW"},
        "moderate": {"days": "3-5", "engineers": "1-2", "risk": "MEDIUM"},
        "complex": {"days": "5-10", "engineers": "2-3", "risk": "HIGH"},
        "very_complex": {"days": "10-20", "engineers": "3-5", "risk": "HIGH"},
    }
    
    complexity = complexity.lower().strip()
    if complexity not in effort_map:
        return f"Unknown complexity '{complexity}'. Use: trivial, simple, moderate, complex, very_complex."
    
    est = effort_map[complexity]
    return (
        f"Effort Estimate: {task_description}\n"
        f"  Complexity: {complexity.upper()}\n"
        f"  Duration: {est['days']} engineering days\n"
        f"  Team Size: {est['engineers']} engineer(s)\n"
        f"  Schedule Risk: {est['risk']}\n"
        f"  Note: Apply 1.5x buffer for first-time implementations. "
        f"Add 2x for integrations with external systems."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Tool Bundles (per-agent tool sets)
# ═══════════════════════════════════════════════════════════════════════════════

DISCOVERY_TOOLS = [web_search]
SOLUTION_DEVISER_TOOLS = [web_search, compare_solutions]
TECHNICAL_ARCHITECT_TOOLS = [web_search]
VERIFIER_TOOLS = [find_contradictions, validate_requirements_completeness]
COMPLIANCE_TOOLS = [web_search, calculate_risk_score, run_stride_analysis]
BUILDER_TOOLS = [estimate_effort]
BUSINESS_ANALYST_TOOLS = [validate_requirements_completeness]

# Agents that use structured generation only (no tools)
# - Business Analyst (may use validation)
# - Data/Integration
# - Test/QA
# - Business Reviewer
# - Synthesizer
