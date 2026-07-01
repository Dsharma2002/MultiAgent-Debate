"""
Pipeline Orchestrator — drives the sequential, verified multi-agent pipeline.

Implements the strict execution protocol:
1. Each agent generates a draft within its Core Specialty
2. The draft passes through the Verification Gate
3. On REJECT: the agent retries once with error feedback
4. On COMMIT: the ledger is updated, and the next agent begins
5. No agent begins until the previous step is [Verified Status: True]
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import yaml

from mad.agents.base import BaseAgent
from mad.agents.loader import load_agents_from_yaml
from mad.constraints.registry import ConstraintRegistry, create_default_registry
from mad.ledger.base import LedgerBackend
from mad.ledger.memory import InMemoryLedger
from mad.pipeline.gate import GateResult, VerificationGate
from mad.schemas.evidence import EvidenceEntry, LedgerSnapshot
from mad.schemas.vocabulary import VocabularyRegistry

logger = logging.getLogger(__name__)


@dataclass
class PipelineStepResult:
    """Result of a single agent's execution step in the pipeline."""

    agent_id: str
    agent_name: str
    attempt: int
    gate_result: GateResult
    success: bool

    def __str__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return f"[{self.agent_name}] {status} (attempt {self.attempt})"


@dataclass
class PipelineResult:
    """Result of the complete pipeline execution."""

    success: bool
    step_results: list[PipelineStepResult] = field(default_factory=list)
    ledger_snapshot: LedgerSnapshot | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def committed_count(self) -> int:
        return sum(1 for s in self.step_results if s.success)

    @property
    def failed_count(self) -> int:
        return sum(1 for s in self.step_results if not s.success)

    def summary(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "steps_completed": self.committed_count,
            "steps_failed": self.failed_count,
            "total_steps": len(self.step_results),
            "ledger_entries": (
                self.ledger_snapshot.total_entries
                if self.ledger_snapshot
                else 0
            ),
            "chain_valid": (
                self.ledger_snapshot.chain_valid
                if self.ledger_snapshot
                else None
            ),
        }


class PipelineOrchestrator:
    """
    Orchestrates the sequential, verified multi-agent pipeline.

    Enforces: "Do not begin generation until previous step
    status is [Verified Status: True]."
    """

    def __init__(
        self,
        agents: list[BaseAgent],
        vocabulary: VocabularyRegistry,
        constraint_registry: ConstraintRegistry,
        ledger: LedgerBackend,
        min_peer_validations: int = 2,
        max_retry_on_reject: int = 1,
    ) -> None:
        self._agents = agents
        self._vocabulary = vocabulary
        self._constraint_registry = constraint_registry
        self._ledger = ledger
        self._max_retry = max_retry_on_reject

        self._gate = VerificationGate(
            vocabulary=vocabulary,
            constraint_registry=constraint_registry,
            ledger=ledger,
            min_peer_validations=min_peer_validations,
        )

    @classmethod
    def from_config(
        cls,
        config_dir: str,
        ledger: LedgerBackend | None = None,
    ) -> PipelineOrchestrator:
        """
        Create a fully-configured orchestrator from config files.

        Reads:
        - config_dir/vocabulary.yaml
        - config_dir/constraints.yaml
        - config_dir/agents.yaml
        """
        # Load vocabulary
        vocab_path = f"{config_dir}/vocabulary.yaml"
        vocabulary = VocabularyRegistry.from_yaml(vocab_path)

        # Load constraints (use defaults + YAML metadata)
        constraint_registry = create_default_registry()
        constraints_path = f"{config_dir}/constraints.yaml"
        try:
            constraint_registry.load_metadata_from_yaml(constraints_path)
        except FileNotFoundError:
            logger.warning(
                f"Constraints file not found at {constraints_path}, "
                f"using defaults"
            )

        # Import builtins to trigger @register_agent decorators
        import mad.agents.builtins.enterprise  # noqa: F401

        # Load agents
        agents_path = f"{config_dir}/agents.yaml"
        agents = load_agents_from_yaml(agents_path, constraint_registry)

        # Load pipeline config
        with open(agents_path, "r") as f:
            agents_config = yaml.safe_load(f)

        pipeline_config = agents_config.get("pipeline", {})
        execution_order = pipeline_config.get("execution_order", [])
        min_peer = pipeline_config.get("min_peer_validations", 2)
        max_retry = pipeline_config.get("max_retry_on_reject", 1)

        # Sort agents by execution order
        if execution_order:
            agent_map = {a.agent_id: a for a in agents}
            ordered_agents = []
            for aid in execution_order:
                if aid in agent_map:
                    ordered_agents.append(agent_map[aid])
                else:
                    logger.warning(
                        f"Agent '{aid}' in execution_order but not defined"
                    )
            agents = ordered_agents

        # Create ledger if not provided
        if ledger is None:
            ledger = InMemoryLedger()

        return cls(
            agents=agents,
            vocabulary=vocabulary,
            constraint_registry=constraint_registry,
            ledger=ledger,
            min_peer_validations=min_peer,
            max_retry_on_reject=max_retry,
        )

    def run(self, context: dict[str, Any]) -> PipelineResult:
        """
        Execute the full pipeline with the given task context.

        Uses a state machine to allow Governance agents (Verifier, Reviewer, Risk)
        to loop the pipeline back to upstream agents if blockers are found.
        """
        logger.info("=" * 60)
        logger.info("PIPELINE EXECUTION STARTED (ENTERPRISE WORKFLOW)")
        logger.info(f"Agents: {[a.agent_id for a in self._agents]}")
        logger.info("=" * 60)

        step_results: list[PipelineStepResult] = []
        pipeline_errors: list[str] = []
        all_success = True

        current_index = 0
        while current_index < len(self._agents):
            agent = self._agents[current_index]
            logger.info(f"\n{'─' * 40}")
            logger.info(f"STEP {current_index + 1}/{len(self._agents)}: {agent.name} ({agent.agent_id})")
            logger.info(f"{'─' * 40}")

            agent_context = self._build_agent_context(context, agent)
            peer_agents = [a for a in self._agents if a.agent_id != agent.agent_id]

            step_result = self._execute_agent_step(
                agent=agent,
                context=agent_context,
                peer_agents=peer_agents,
            )
            step_results.append(step_result)

            # Check if this agent generated blockers (e.g. Governance Agents)
            # In Phase 1 we look at the last ledger entry added by this agent
            last_entry = self._ledger.get_latest()
            has_blockers = False
            if last_entry and last_entry.author_agent_id == agent.agent_id:
                blockers = last_entry.content.get("blockers", [])
                if blockers:
                    has_blockers = True
                    logger.warning(f"[{agent.agent_id}] found {len(blockers)} blockers: {blockers}")

            if not step_result.success or has_blockers:
                if agent.agent_id in ["verifier", "business_reviewer", "compliance_risk"]:
                    # Governance loopback!
                    logger.warning(f"[Pipeline] {agent.name} threw a blocker. Looping back to Solution Deviser.")
                    # Jump back to solution_deviser (index 2)
                    current_index = 2
                    continue
                else:
                    all_success = False
                    error_msg = f"Agent '{agent.agent_id}' failed."
                    pipeline_errors.append(error_msg)
                    logger.error(f"[Pipeline] {error_msg}")
                    # If a core agent fails completely, we break out for now
                    break

            # Proceed to next agent
            current_index += 1

        snapshot = self._ledger.snapshot()

        logger.info(f"\n{'=' * 60}")
        logger.info("PIPELINE EXECUTION COMPLETE")
        logger.info(f"Success: {all_success}")
        logger.info(f"Committed: {snapshot.verified_entries}")
        logger.info(f"{'=' * 60}")

        return PipelineResult(
            success=all_success,
            step_results=step_results,
            ledger_snapshot=snapshot,
            errors=pipeline_errors,
        )

    def _execute_agent_step(
        self,
        agent: BaseAgent,
        context: dict[str, Any],
        peer_agents: list[BaseAgent],
    ) -> PipelineStepResult:
        """
        Execute a single agent step with retry on rejection.

        Protocol:
        1. Agent generates a draft (core_execute)
        2. Draft goes through Verification Gate
        3. On REJECT: retry once with error feedback
        4. On COMMIT: return success
        """
        last_gate_result: GateResult | None = None

        for attempt in range(1, self._max_retry + 2):  # +2 because range is exclusive
            logger.info(f"[{agent.agent_id}] Attempt {attempt}")

            # ── Step 1: Local Draft ───────────────────────────────────────
            try:
                draft = agent.core_execute(context, self._ledger)
                logger.info(
                    f"[{agent.agent_id}] Draft generated: "
                    f"entry_id={draft.entry_id}"
                )
            except Exception as e:
                logger.error(f"[{agent.agent_id}] core_execute failed: {e}")
                return PipelineStepResult(
                    agent_id=agent.agent_id,
                    agent_name=agent.name,
                    attempt=attempt,
                    gate_result=GateResult(
                        committed=False,
                        errors=[f"core_execute error: {e}"],
                    ),
                    success=False,
                )

            # ── Steps 2-4: Verification Gate ──────────────────────────────
            gate_result = self._gate.verify(draft, peer_agents)
            last_gate_result = gate_result

            if gate_result.committed:
                logger.info(f"[{agent.agent_id}] Entry COMMITTED on attempt {attempt}")
                return PipelineStepResult(
                    agent_id=agent.agent_id,
                    agent_name=agent.name,
                    attempt=attempt,
                    gate_result=gate_result,
                    success=True,
                )

            # REJECTED — provide feedback for retry
            logger.warning(
                f"[{agent.agent_id}] REJECTED on attempt {attempt}: "
                f"{gate_result.errors}"
            )

            if attempt <= self._max_retry:
                # Inject error feedback into context for the retry
                context = dict(context)
                context["_rejection_feedback"] = gate_result.errors
                context["_retry_attempt"] = attempt + 1
                logger.info(
                    f"[{agent.agent_id}] Retrying with error feedback..."
                )

        # All attempts exhausted
        logger.error(
            f"[{agent.agent_id}] Failed after {self._max_retry + 1} attempts"
        )
        return PipelineStepResult(
            agent_id=agent.agent_id,
            agent_name=agent.name,
            attempt=self._max_retry + 1,
            gate_result=last_gate_result or GateResult(committed=False),
            success=False,
        )

    def _build_agent_context(
        self,
        original_context: dict[str, Any],
        agent: BaseAgent,
    ) -> dict[str, Any]:
        """
        Build the execution context for an agent.

        Merges the original task context with relevant ledger state
        so the agent can build on previously verified entries.
        """
        context = dict(original_context)

        # Add ledger summary
        verified = self._ledger.get_all(verified_only=True)
        context["_ledger_verified_count"] = len(verified)
        context["_ledger_total_budget"] = self._ledger.get_total_budget()

        # Add previous agent assessments for context
        if verified:
            context["_prior_assessments"] = [
                {
                    "agent": e.author_agent_id,
                    "type": e.content.get("assessment_type"),
                    "summary": e.content.get("description", "")[:100],
                }
                for e in verified
            ]

        return context
