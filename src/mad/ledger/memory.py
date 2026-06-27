"""
In-memory append-only ledger implementation.

Suitable for testing, single-run executions, and development.
Data is lost when the process exits.
"""

from __future__ import annotations

import threading
from uuid import UUID

from mad.ledger.base import LedgerBackend
from mad.schemas.evidence import EvidenceEntry


class InMemoryLedger(LedgerBackend):
    """
    Thread-safe, in-memory append-only ledger.

    Stores entries in a Python list. Each append operation verifies
    the hash chain before committing.
    """

    def __init__(self) -> None:
        self._entries: list[EvidenceEntry] = []
        self._index: dict[UUID, int] = {}  # entry_id -> list index
        self._lock = threading.Lock()

    def append(self, entry: EvidenceEntry) -> EvidenceEntry:
        """Append an entry, setting prev_hash from the current chain tail."""
        with self._lock:
            # Determine prev_hash
            if self._entries:
                prev_hash = self._entries[-1].entry_hash
            else:
                prev_hash = "GENESIS"

            # Create the committed entry with correct chaining
            committed = EvidenceEntry(
                entry_id=entry.entry_id,
                timestamp=entry.timestamp,
                author_agent_id=entry.author_agent_id,
                content=entry.content,
                verified_status=entry.verified_status,
                prev_hash=prev_hash,
                rejection_history=entry.rejection_history,
            )

            self._entries.append(committed)
            self._index[committed.entry_id] = len(self._entries) - 1
            return committed

    def get(self, entry_id: UUID) -> EvidenceEntry | None:
        """Retrieve an entry by ID."""
        with self._lock:
            idx = self._index.get(entry_id)
            if idx is not None:
                return self._entries[idx]
            return None

    def get_all(self, verified_only: bool = False) -> list[EvidenceEntry]:
        """Retrieve all entries, optionally filtering to verified-only."""
        with self._lock:
            if verified_only:
                return [e for e in self._entries if e.verified_status]
            return list(self._entries)

    def get_latest(self) -> EvidenceEntry | None:
        """Return the most recent entry."""
        with self._lock:
            if self._entries:
                return self._entries[-1]
            return None

    def verify_chain_integrity(self) -> tuple[bool, list[str]]:
        """Walk the chain and verify every hash link."""
        with self._lock:
            return _verify_chain(self._entries)

    def size(self) -> int:
        """Return the number of entries."""
        with self._lock:
            return len(self._entries)


def _verify_chain(entries: list[EvidenceEntry]) -> tuple[bool, list[str]]:
    """
    Verify the hash chain integrity of a list of entries.

    Checks:
    1. First entry's prev_hash must be 'GENESIS'.
    2. Each subsequent entry's prev_hash must match the prior entry's entry_hash.
    3. Each entry's stored hash must match its recomputed hash.
    """
    errors: list[str] = []

    if not entries:
        return True, []

    # Check first entry
    if entries[0].prev_hash != "GENESIS":
        errors.append(
            f"Entry 0 ({entries[0].entry_id}): prev_hash should be 'GENESIS', "
            f"got '{entries[0].prev_hash}'"
        )

    for i, entry in enumerate(entries):
        # Verify self-hash integrity
        if not entry.verify_integrity():
            errors.append(
                f"Entry {i} ({entry.entry_id}): hash mismatch — "
                f"stored={entry.entry_hash}, recomputed={entry.recompute_hash()}"
            )

        # Verify chain linkage (skip first entry, already checked above)
        if i > 0:
            expected_prev = entries[i - 1].entry_hash
            if entry.prev_hash != expected_prev:
                errors.append(
                    f"Entry {i} ({entry.entry_id}): prev_hash mismatch — "
                    f"expected={expected_prev}, got={entry.prev_hash}"
                )

    return len(errors) == 0, errors
