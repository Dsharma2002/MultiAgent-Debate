"""
Event System — granular pipeline event capture for real-time streaming.

Hooks into the existing Orchestrator and VerificationGate to emit
structured events without modifying their core logic. Events are
dispatched to registered listeners (e.g., the WebSocket handler).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from uuid import uuid4


class EventType(str, Enum):
    """All event types emitted during pipeline execution."""

    PIPELINE_START = "pipeline_start"
    PIPELINE_COMPLETE = "pipeline_complete"
    AGENT_START = "agent_start"
    AGENT_COMPLETE = "agent_complete"
    DRAFT_CREATED = "draft_created"
    VOCAB_CHECK = "vocab_check"
    CONSTRAINT_CHECK = "constraint_check"
    PEER_AUDIT_START = "peer_audit_start"
    PEER_AUDIT_RESULT = "peer_audit_result"
    GATE_DECISION = "gate_decision"
    RETRY = "retry"
    ERROR = "error"


@dataclass
class PipelineEvent:
    """A single event emitted during pipeline execution."""

    event_type: EventType
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: str(uuid4())[:8])
    agent_id: str | None = None
    agent_name: str | None = None
    step_index: int | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict for WebSocket transmission."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "event_id": self.event_id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "step_index": self.step_index,
            "data": self.data,
        }


# Type alias for event listener callbacks
EventListener = Callable[[PipelineEvent], None]


class EventEmitter:
    """
    Central event dispatcher for the pipeline.

    Register listeners to receive real-time events.
    Thread-safe for use with the synchronous pipeline.
    """

    def __init__(self) -> None:
        self._listeners: list[EventListener] = []

    def on(self, listener: EventListener) -> None:
        """Register an event listener."""
        self._listeners.append(listener)

    def off(self, listener: EventListener) -> None:
        """Unregister an event listener."""
        self._listeners = [l for l in self._listeners if l is not listener]

    def emit(self, event: PipelineEvent) -> None:
        """Dispatch an event to all registered listeners."""
        for listener in self._listeners:
            try:
                listener(event)
            except Exception:
                pass  # Don't let listener errors crash the pipeline

    def clear(self) -> None:
        """Remove all listeners."""
        self._listeners.clear()
