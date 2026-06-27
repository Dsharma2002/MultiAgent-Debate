"""
Agent Loader — instantiates agents from YAML configuration.

The loader reads agent definitions from a YAML file and creates
the appropriate agent instances using the class registry.
"""

from __future__ import annotations

from typing import Any

import yaml

from mad.agents.base import BaseAgent, _AGENT_CLASS_REGISTRY
from mad.constraints.registry import ConstraintRegistry


def load_agents_from_yaml(
    config_path: str,
    constraint_registry: ConstraintRegistry,
) -> list[BaseAgent]:
    """
    Load and instantiate agents from a YAML config file.

    The YAML format:
        agents:
          - agent_id: tech_lead
            agent_type: tech_lead
            name: "Tech Lead"
            core_specialty: "Database optimization, backend architecture..."
            audit_constraints:
              - constraint_01
              - constraint_03

    Each agent_type must have a corresponding registered class.
    """
    with open(config_path, "r") as f:
        raw = yaml.safe_load(f)

    agents: list[BaseAgent] = []
    for agent_data in raw.get("agents", []):
        agent = _create_agent(agent_data, constraint_registry)
        agents.append(agent)

    return agents


def _create_agent(
    config: dict[str, Any],
    constraint_registry: ConstraintRegistry,
) -> BaseAgent:
    """Create a single agent instance from its config dict."""
    agent_type = config.get("agent_type", config.get("agent_id"))

    if agent_type not in _AGENT_CLASS_REGISTRY:
        available = list(_AGENT_CLASS_REGISTRY.keys())
        raise ValueError(
            f"Unknown agent_type '{agent_type}'. "
            f"Available types: {available}. "
            f"Register with @register_agent('{agent_type}')."
        )

    agent_cls = _AGENT_CLASS_REGISTRY[agent_type]

    agent = agent_cls(
        agent_id=config["agent_id"],
        name=config.get("name", agent_type),
        core_specialty=config.get("core_specialty", ""),
        audit_constraints=config.get("audit_constraints", []),
        constraint_registry=constraint_registry,
    )

    return agent


def list_available_agent_types() -> list[str]:
    """Return a list of all registered agent type names."""
    return list(_AGENT_CLASS_REGISTRY.keys())
