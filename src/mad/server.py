"""
FastAPI Server — real-time WebSocket API for the MAD pipeline dashboard.

Provides:
- /ws/pipeline — WebSocket endpoint streaming pipeline events
- /api/config — Agent and constraint configuration
- /api/ledger — Current ledger state
- /api/pipeline/run — REST trigger for pipeline execution
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import yaml

from mad.events import EventEmitter, EventType, PipelineEvent
from mad.ledger.memory import InMemoryLedger
from mad.pipeline.orchestrator import PipelineOrchestrator

logger = logging.getLogger(__name__)

# ─── App Setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="MAD Pipeline Dashboard API",
    description="Real-time multi-agent debate pipeline visualization",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Config directory path
CONFIG_DIR = str(Path(__file__).parent.parent.parent / "config")

# Global ledger (persists across requests within one server session)
_ledger = InMemoryLedger()


def _reset_ledger() -> None:
    global _ledger
    _ledger = InMemoryLedger()


# ─── REST Endpoints ──────────────────────────────────────────────────────────

@app.get("/api/config")
async def get_config() -> dict[str, Any]:
    """Return agent definitions and constraint metadata."""
    agents_path = f"{CONFIG_DIR}/agents.yaml"
    constraints_path = f"{CONFIG_DIR}/constraints.yaml"

    with open(agents_path) as f:
        agents_data = yaml.safe_load(f)
    with open(constraints_path) as f:
        constraints_data = yaml.safe_load(f)

    return {
        "agents": agents_data.get("agents", []),
        "pipeline": agents_data.get("pipeline", {}),
        "constraints": constraints_data.get("constraints", []),
    }


@app.get("/api/ledger")
async def get_ledger() -> dict[str, Any]:
    """Return current ledger state."""
    entries = _ledger.get_all()
    is_valid, errors = _ledger.verify_chain_integrity()
    return {
        "entries": [
            {
                "entry_id": str(e.entry_id),
                "author_agent_id": e.author_agent_id,
                "content": e.content,
                "verified_status": e.verified_status,
                "entry_hash": e.entry_hash[:16],
                "prev_hash": e.prev_hash[:16] if e.prev_hash != "GENESIS" else "GENESIS",
                "timestamp": e.timestamp.isoformat(),
            }
            for e in entries
        ],
        "total_entries": len(entries),
        "verified_entries": sum(1 for e in entries if e.verified_status),
        "total_budget": _ledger.get_total_budget(),
        "chain_valid": is_valid,
    }


@app.get("/api/scenarios")
async def get_scenarios() -> list[dict[str, Any]]:
    """Return preset demo scenarios."""
    return [
        {
            "id": "notification-system",
            "name": "🔔 Real-Time Notification System",
            "description": (
                "Build a real-time notification system with WebSocket support, "
                "user preference management, and API rate limiting. Requires "
                "database schema for notification storage and authentication integration."
            ),
            "budget": 2500,
            "complexity": "high",
            "user_impact": "high",
            "effort": "medium",
            "database": "PostgreSQL v15 with TimescaleDB",
            "scale_requirements": "10,000 concurrent connections",
        },
        {
            "id": "user-dashboard",
            "name": "📊 Analytics Dashboard",
            "description": (
                "Create a user analytics dashboard with data visualization, "
                "custom report generation, and export functionality."
            ),
            "budget": 1500,
            "complexity": "medium",
            "user_impact": "high",
            "effort": "medium",
        },
        {
            "id": "payment-gateway",
            "name": "💳 Payment Gateway Integration",
            "description": (
                "Integrate secure payment processing with PII handling, "
                "credit card tokenization, and PCI compliance requirements. "
                "Requires encryption at rest and audit logging."
            ),
            "budget": 3500,
            "complexity": "high",
            "user_impact": "medium",
            "effort": "high",
            "security_classification": "high",
        },
        {
            "id": "simple-api",
            "name": "🚀 REST API Microservice",
            "description": (
                "Build a lightweight REST API microservice for user management "
                "with CRUD operations and input validation."
            ),
            "budget": 800,
            "complexity": "low",
            "user_impact": "medium",
            "effort": "low",
        },
    ]


# ─── WebSocket Pipeline Execution ─────────────────────────────────────────────

@app.websocket("/ws/pipeline")
async def websocket_pipeline(ws: WebSocket) -> None:
    """
    WebSocket endpoint that runs the pipeline and streams events in real-time.

    Client sends a JSON message with the proposal context to start execution.
    Server streams PipelineEvent objects as JSON messages.
    """
    await ws.accept()

    try:
        # Wait for the client to send a proposal context
        raw = await ws.receive_text()
        context = json.loads(raw)

        # Ensure proposal_id
        if "proposal_id" not in context:
            context["proposal_id"] = str(uuid4())

        # Reset ledger for fresh run
        _reset_ledger()

        # Set up event emitter → WebSocket bridge
        emitter = EventEmitter()
        event_queue: asyncio.Queue[PipelineEvent] = asyncio.Queue()

        def on_event(event: PipelineEvent) -> None:
            """Thread-safe bridge: pipeline thread → async queue."""
            try:
                event_queue.put_nowait(event)
            except asyncio.QueueFull:
                pass

        emitter.on(on_event)

        # Run pipeline in a thread (it's synchronous) and stream events
        async def run_pipeline() -> None:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                _run_instrumented_pipeline,
                context,
                emitter,
            )

        pipeline_task = asyncio.create_task(run_pipeline())

        # Stream events to client as they arrive
        try:
            while True:
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                    await ws.send_json(event.to_dict())

                    # If pipeline is complete, send remaining events and exit
                    if event.event_type == EventType.PIPELINE_COMPLETE:
                        # Drain any remaining events
                        while not event_queue.empty():
                            remaining = event_queue.get_nowait()
                            await ws.send_json(remaining.to_dict())
                        break
                except asyncio.TimeoutError:
                    # Check if pipeline task finished (error case)
                    if pipeline_task.done():
                        exc = pipeline_task.exception()
                        if exc:
                            await ws.send_json(
                                PipelineEvent(
                                    event_type=EventType.ERROR,
                                    data={"error": str(exc)},
                                ).to_dict()
                            )
                        break
        except WebSocketDisconnect:
            pipeline_task.cancel()
            return

        # Wait for pipeline to fully finish
        await pipeline_task

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except json.JSONDecodeError:
        await ws.send_json({"error": "Invalid JSON in request"})
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await ws.send_json(
                PipelineEvent(
                    event_type=EventType.ERROR,
                    data={"error": str(e)},
                ).to_dict()
            )
        except Exception:
            pass


def _run_instrumented_pipeline(
    context: dict[str, Any],
    emitter: EventEmitter,
) -> None:
    """
    Run the pipeline with event instrumentation.

    This wraps the standard orchestrator with event emission at every step.
    """
    # Import builtins to trigger registration
    import mad.agents.builtins.tech_lead  # noqa: F401
    import mad.agents.builtins.product_manager  # noqa: F401
    import mad.agents.builtins.qa_engineer  # noqa: F401
    import mad.agents.builtins.security_auditor  # noqa: F401

    from mad.agents.loader import load_agents_from_yaml
    from mad.constraints.registry import create_default_registry
    from mad.constraints.evaluator import ConstraintEvaluator
    from mad.schemas.vocabulary import VocabularyRegistry
    from mad.pipeline.gate import VerificationGate

    # Load config
    vocab = VocabularyRegistry.from_yaml(f"{CONFIG_DIR}/vocabulary.yaml")
    constraints = create_default_registry()
    agents = load_agents_from_yaml(f"{CONFIG_DIR}/agents.yaml", constraints)

    # Load pipeline config
    with open(f"{CONFIG_DIR}/agents.yaml") as f:
        agents_config = yaml.safe_load(f)
    pipeline_config = agents_config.get("pipeline", {})
    execution_order = pipeline_config.get("execution_order", [])
    min_peer = pipeline_config.get("min_peer_validations", 2)
    max_retry = pipeline_config.get("max_retry_on_reject", 1)

    # Sort agents by execution order
    if execution_order:
        agent_map = {a.agent_id: a for a in agents}
        agents = [agent_map[aid] for aid in execution_order if aid in agent_map]

    # Create gate
    gate = VerificationGate(
        vocabulary=vocab,
        constraint_registry=constraints,
        ledger=_ledger,
        min_peer_validations=min_peer,
    )

    evaluator = ConstraintEvaluator(constraints)

    # ── PIPELINE_START ────────────────────────────────────────────────
    emitter.emit(PipelineEvent(
        event_type=EventType.PIPELINE_START,
        data={
            "context": context,
            "agents": [
                {"agent_id": a.agent_id, "name": a.name, "specialty": a.core_specialty}
                for a in agents
            ],
            "total_steps": len(agents),
        },
    ))

    import time

    results = []
    for step_idx, agent in enumerate(agents):
        peer_agents = [a for a in agents if a.agent_id != agent.agent_id]

        # ── AGENT_START ───────────────────────────────────────────────
        emitter.emit(PipelineEvent(
            event_type=EventType.AGENT_START,
            agent_id=agent.agent_id,
            agent_name=agent.name,
            step_index=step_idx,
            data={"specialty": agent.core_specialty},
        ))
        time.sleep(0.6)  # Pacing for UI animation

        # Retry loop
        success = False
        for attempt in range(1, max_retry + 2):
            # Build context
            agent_context = dict(context)
            verified = _ledger.get_all(verified_only=True)
            agent_context["_ledger_verified_count"] = len(verified)
            agent_context["_ledger_total_budget"] = _ledger.get_total_budget()

            # ── DRAFT_CREATED ─────────────────────────────────────────
            try:
                draft = agent.core_execute(agent_context, _ledger)
                emitter.emit(PipelineEvent(
                    event_type=EventType.DRAFT_CREATED,
                    agent_id=agent.agent_id,
                    agent_name=agent.name,
                    step_index=step_idx,
                    data={
                        "entry_id": str(draft.entry_id),
                        "content": draft.content,
                        "attempt": attempt,
                    },
                ))
                time.sleep(0.4)
            except Exception as e:
                emitter.emit(PipelineEvent(
                    event_type=EventType.ERROR,
                    agent_id=agent.agent_id,
                    step_index=step_idx,
                    data={"error": str(e), "phase": "core_execute"},
                ))
                break

            # ── VOCAB_CHECK ───────────────────────────────────────────
            vocab_errors = vocab.validate_data(draft.content)
            emitter.emit(PipelineEvent(
                event_type=EventType.VOCAB_CHECK,
                agent_id=agent.agent_id,
                step_index=step_idx,
                data={
                    "passed": len(vocab_errors) == 0,
                    "errors": vocab_errors,
                    "keys_checked": list(draft.content.keys()),
                },
            ))
            time.sleep(0.3)

            if vocab_errors:
                emitter.emit(PipelineEvent(
                    event_type=EventType.GATE_DECISION,
                    agent_id=agent.agent_id,
                    step_index=step_idx,
                    data={
                        "decision": "REJECT",
                        "reason": "vocabulary_violation",
                        "errors": vocab_errors,
                    },
                ))
                if attempt <= max_retry:
                    emitter.emit(PipelineEvent(
                        event_type=EventType.RETRY,
                        agent_id=agent.agent_id,
                        step_index=step_idx,
                        data={"attempt": attempt + 1, "reason": vocab_errors},
                    ))
                    time.sleep(0.3)
                continue

            # ── CONSTRAINT_CHECK ──────────────────────────────────────
            constraint_result = evaluator.evaluate(entry=draft, ledger=_ledger)
            emitter.emit(PipelineEvent(
                event_type=EventType.CONSTRAINT_CHECK,
                agent_id=agent.agent_id,
                step_index=step_idx,
                data={
                    "passed": constraint_result.passed,
                    "violations": constraint_result.violations,
                },
            ))
            time.sleep(0.3)

            if not constraint_result.passed:
                emitter.emit(PipelineEvent(
                    event_type=EventType.GATE_DECISION,
                    agent_id=agent.agent_id,
                    step_index=step_idx,
                    data={
                        "decision": "REJECT",
                        "reason": "constraint_violation",
                        "errors": constraint_result.violations,
                    },
                ))
                if attempt <= max_retry:
                    emitter.emit(PipelineEvent(
                        event_type=EventType.RETRY,
                        agent_id=agent.agent_id,
                        step_index=step_idx,
                        data={"attempt": attempt + 1, "reason": constraint_result.violations},
                    ))
                    time.sleep(0.3)
                continue

            # ── PEER_AUDIT ────────────────────────────────────────────
            emitter.emit(PipelineEvent(
                event_type=EventType.PEER_AUDIT_START,
                agent_id=agent.agent_id,
                step_index=step_idx,
                data={
                    "peers": [p.agent_id for p in peer_agents],
                    "min_required": min_peer,
                },
            ))
            time.sleep(0.3)

            approval_count = 0
            audit_errors = []
            for peer in peer_agents:
                audit_result = peer.audit(draft, _ledger)
                emitter.emit(PipelineEvent(
                    event_type=EventType.PEER_AUDIT_RESULT,
                    agent_id=agent.agent_id,
                    step_index=step_idx,
                    data={
                        "auditor_id": peer.agent_id,
                        "auditor_name": peer.name,
                        "approved": audit_result.approved,
                        "reasons": audit_result.rejection_reasons,
                    },
                ))
                time.sleep(0.4)

                if audit_result.approved:
                    approval_count += 1
                else:
                    for r in audit_result.rejection_reasons:
                        audit_errors.append(f"[{peer.agent_id}] {r}")

            # ── GATE_DECISION ─────────────────────────────────────────
            all_errors = audit_errors
            if approval_count < min_peer:
                all_errors.append(
                    f"Insufficient approvals: {approval_count}/{min_peer}"
                )

            if all_errors:
                emitter.emit(PipelineEvent(
                    event_type=EventType.GATE_DECISION,
                    agent_id=agent.agent_id,
                    step_index=step_idx,
                    data={
                        "decision": "REJECT",
                        "reason": "peer_audit_failure",
                        "errors": all_errors,
                        "approvals": approval_count,
                        "required": min_peer,
                    },
                ))
                if attempt <= max_retry:
                    emitter.emit(PipelineEvent(
                        event_type=EventType.RETRY,
                        agent_id=agent.agent_id,
                        step_index=step_idx,
                        data={"attempt": attempt + 1, "reason": all_errors},
                    ))
                    time.sleep(0.3)
                continue

            # COMMIT
            verified_content = dict(draft.content)
            verified_content["peer_validations"] = approval_count
            from mad.schemas.evidence import EvidenceEntry

            latest = _ledger.get_latest()
            prev_hash = latest.entry_hash if latest else "GENESIS"
            verified_entry = EvidenceEntry(
                entry_id=draft.entry_id,
                timestamp=draft.timestamp,
                author_agent_id=draft.author_agent_id,
                content=verified_content,
                verified_status=True,
                prev_hash=prev_hash,
            )
            committed = _ledger.append(verified_entry)

            emitter.emit(PipelineEvent(
                event_type=EventType.GATE_DECISION,
                agent_id=agent.agent_id,
                step_index=step_idx,
                data={
                    "decision": "COMMIT",
                    "entry_id": str(committed.entry_id),
                    "entry_hash": committed.entry_hash[:16],
                    "prev_hash": committed.prev_hash[:16] if committed.prev_hash != "GENESIS" else "GENESIS",
                    "approvals": approval_count,
                    "budget_used": _ledger.get_total_budget(),
                    "content": committed.content,
                },
            ))
            success = True
            time.sleep(0.3)
            break

        # ── AGENT_COMPLETE ────────────────────────────────────────────
        emitter.emit(PipelineEvent(
            event_type=EventType.AGENT_COMPLETE,
            agent_id=agent.agent_id,
            agent_name=agent.name,
            step_index=step_idx,
            data={"success": success},
        ))
        results.append({"agent_id": agent.agent_id, "success": success})
        time.sleep(0.5)

    # ── PIPELINE_COMPLETE ─────────────────────────────────────────────
    snapshot = _ledger.snapshot()
    emitter.emit(PipelineEvent(
        event_type=EventType.PIPELINE_COMPLETE,
        data={
            "success": all(r["success"] for r in results),
            "results": results,
            "ledger": {
                "total_entries": snapshot.total_entries,
                "verified_entries": snapshot.verified_entries,
                "chain_valid": snapshot.chain_valid,
                "total_budget": _ledger.get_total_budget(),
            },
        },
    ))
