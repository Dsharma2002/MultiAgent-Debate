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

from dotenv import load_dotenv
load_dotenv()

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
    Run the LangGraph consensus engine with event streaming.

    This replaces the old manual pipeline with a compiled LangGraph StateGraph.
    Each node in the graph emits PipelineEvents for the dashboard via the emitter
    passed through LangGraph's configurable context.
    """
    import time
    from mad.graph import build_consensus_graph, AGENT_META, TOTAL_AGENTS

    # ── PIPELINE_START ────────────────────────────────────────────────
    emitter.emit(PipelineEvent(
        event_type=EventType.PIPELINE_START,
        data={
            "context": context,
            "agents": [
                {"agent_id": aid, "name": meta["name"], "specialty": meta["specialty"]}
                for aid, meta in AGENT_META.items()
            ],
            "total_steps": TOTAL_AGENTS,
        },
    ))
    time.sleep(0.3)

    # ── Build and run the LangGraph ───────────────────────────────────
    graph = build_consensus_graph()

    # Initial state for the Blackboard
    initial_state = {
        "proposal_text": context.get("description", context.get("proposal", "")),
        "proposal_id": context.get("proposal_id", ""),
        "current_phase": "init",
        "iteration_count": 0,
        "consensus_score": 0.0,
    }

    # Run the graph, passing emitter and ledger through config
    try:
        final_state = graph.invoke(
            initial_state,
            config={
                "configurable": {
                    "emitter": emitter,
                    "ledger": _ledger,
                },
            },
        )

        # ── PIPELINE_COMPLETE ─────────────────────────────────────────
        snapshot = _ledger.snapshot()
        synthesis = final_state.get("final_synthesis", {})

        emitter.emit(PipelineEvent(
            event_type=EventType.PIPELINE_COMPLETE,
            data={
                "success": True,
                "results": [
                    {"agent_id": t.get("agent_id", "unknown"), "success": True}
                    for t in final_state.get("agent_trace", [])
                ],
                "consensus": {
                    "score": final_state.get("consensus_score", 0.0),
                    "verdict": synthesis.get("verdict", "UNKNOWN"),
                    "executive_summary": synthesis.get("executive_summary", ""),
                },
                "ledger": {
                    "total_entries": snapshot.total_entries,
                    "verified_entries": snapshot.verified_entries,
                    "chain_valid": snapshot.chain_valid,
                    "total_budget": _ledger.get_total_budget(),
                },
            },
        ))

    except Exception as e:
        logger.error(f"LangGraph pipeline failed: {e}", exc_info=True)
        emitter.emit(PipelineEvent(
            event_type=EventType.ERROR,
            data={"error": str(e), "phase": "langgraph_execution"},
        ))
        # Emit pipeline complete with failure
        snapshot = _ledger.snapshot()
        emitter.emit(PipelineEvent(
            event_type=EventType.PIPELINE_COMPLETE,
            data={
                "success": False,
                "results": [],
                "ledger": {
                    "total_entries": snapshot.total_entries,
                    "verified_entries": snapshot.verified_entries,
                    "chain_valid": snapshot.chain_valid,
                    "total_budget": _ledger.get_total_budget(),
                },
                "error": str(e),
            },
        ))

