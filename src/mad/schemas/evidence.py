"""
Evidence Entry and Ledger Snapshot models.

Every piece of data entering the Shared Evidence layer is represented as an
EvidenceEntry — an immutable, hash-chained record in the Truth Ledger.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, computed_field


def _canonical_json(data: dict[str, Any]) -> str:
    """
    Produce a canonical JSON string for deterministic hashing.

    Keys are sorted, no extra whitespace, datetimes converted to ISO strings.
    """

    def _default(obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=_default)


def compute_entry_hash(
    entry_id: UUID,
    timestamp: datetime,
    author_agent_id: str,
    content: dict[str, Any],
    verified_status: bool,
    prev_hash: str,
) -> str:
    """Compute the SHA-256 hash of an evidence entry's canonical data."""
    canonical_data = {
        "entry_id": str(entry_id),
        "timestamp": timestamp.isoformat(),
        "author_agent_id": author_agent_id,
        "content": content,
        "verified_status": verified_status,
        "prev_hash": prev_hash,
    }
    canonical_str = _canonical_json(canonical_data)
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


class EvidenceEntry(BaseModel):
    """
    A single entry in the Truth Ledger.

    Each entry is hash-chained to the previous entry for tamper detection.
    Once created with verified_status=True and committed, the entry is
    considered immutable.
    """

    entry_id: UUID = Field(default_factory=uuid4, description="Unique entry identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of entry creation",
    )
    author_agent_id: str = Field(description="ID of the agent that authored this entry")
    content: dict[str, Any] = Field(
        description="Entry payload — must conform to Shared Vocabulary"
    )
    verified_status: bool = Field(
        default=False,
        description="True only after passing the Verification Gate",
    )
    prev_hash: str = Field(
        default="GENESIS",
        description="SHA-256 hash of the previous entry (or 'GENESIS' for the first)",
    )
    entry_hash: str = Field(
        default="",
        description="SHA-256 hash of this entry's canonical data",
    )
    rejection_history: list[str] = Field(
        default_factory=list,
        description="Log of rejection reasons if this entry was rejected before being committed",
    )

    def model_post_init(self, _context: Any) -> None:
        """Compute entry_hash after all fields are set."""
        if not self.entry_hash:
            self.entry_hash = compute_entry_hash(
                entry_id=self.entry_id,
                timestamp=self.timestamp,
                author_agent_id=self.author_agent_id,
                content=self.content,
                verified_status=self.verified_status,
                prev_hash=self.prev_hash,
            )

    def recompute_hash(self) -> str:
        """Recompute and return the hash (for integrity verification)."""
        return compute_entry_hash(
            entry_id=self.entry_id,
            timestamp=self.timestamp,
            author_agent_id=self.author_agent_id,
            content=self.content,
            verified_status=self.verified_status,
            prev_hash=self.prev_hash,
        )

    def verify_integrity(self) -> bool:
        """Check if the stored hash matches the recomputed hash."""
        return self.entry_hash == self.recompute_hash()

    def as_verified(self, prev_hash: str) -> EvidenceEntry:
        """
        Create a new verified copy of this entry with proper hash chaining.

        This is used by the VerificationGate to produce the committed version.
        """
        return EvidenceEntry(
            entry_id=self.entry_id,
            timestamp=self.timestamp,
            author_agent_id=self.author_agent_id,
            content=self.content,
            verified_status=True,
            prev_hash=prev_hash,
            rejection_history=self.rejection_history,
        )


class LedgerSnapshot(BaseModel):
    """
    A complete snapshot of the Truth Ledger at a point in time.

    Used for serialization, reporting, and integrity auditing.
    """

    snapshot_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    entries: list[EvidenceEntry] = Field(default_factory=list)
    chain_valid: bool = Field(
        default=True, description="Whether the hash chain is intact"
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_entries(self) -> int:
        return len(self.entries)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def verified_entries(self) -> int:
        return sum(1 for e in self.entries if e.verified_status)

    def to_summary(self) -> dict[str, Any]:
        """Return a human-readable summary of the ledger state."""
        return {
            "snapshot_id": str(self.snapshot_id),
            "created_at": self.created_at.isoformat(),
            "total_entries": self.total_entries,
            "verified_entries": self.verified_entries,
            "chain_valid": self.chain_valid,
        }
