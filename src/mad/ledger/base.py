"""
Abstract base class for Ledger backends.

All ledger implementations must follow the append-only contract:
entries can only be added, never modified or deleted.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from mad.schemas.evidence import EvidenceEntry, LedgerSnapshot


class LedgerBackend(ABC):
    """
    Abstract interface for the Truth Ledger storage.

    Implementations must guarantee:
    1. Append-only semantics — no entry can be modified or deleted after commit.
    2. Hash-chain integrity — each entry's prev_hash links to the prior entry.
    3. Thread-safe operations for concurrent agent access.
    """

    @abstractmethod
    def append(self, entry: EvidenceEntry) -> EvidenceEntry:
        """
        Append a verified entry to the ledger.

        The implementation must set the entry's prev_hash to the hash of
        the most recent entry (or 'GENESIS' if this is the first entry).

        Returns the committed entry with its final hash.
        """
        ...

    @abstractmethod
    def get(self, entry_id: UUID) -> EvidenceEntry | None:
        """Retrieve an entry by its ID. Returns None if not found."""
        ...

    @abstractmethod
    def get_all(self, verified_only: bool = False) -> list[EvidenceEntry]:
        """
        Retrieve all entries in the ledger.

        If verified_only is True, only return entries with verified_status=True.
        """
        ...

    @abstractmethod
    def get_latest(self) -> EvidenceEntry | None:
        """Return the most recently appended entry, or None if the ledger is empty."""
        ...

    @abstractmethod
    def verify_chain_integrity(self) -> tuple[bool, list[str]]:
        """
        Walk the entire chain and verify hash integrity.

        Returns (is_valid, list_of_error_messages).
        """
        ...

    @abstractmethod
    def size(self) -> int:
        """Return the number of entries in the ledger."""
        ...

    def snapshot(self) -> LedgerSnapshot:
        """Create a LedgerSnapshot of the current ledger state."""
        entries = self.get_all()
        is_valid, _ = self.verify_chain_integrity()
        return LedgerSnapshot(entries=entries, chain_valid=is_valid)

    def get_total_budget(self) -> int:
        """
        Sum all budget_allocation values from verified entries.

        Utility method used by budget-related constraints.
        """
        total = 0
        for entry in self.get_all(verified_only=True):
            budget = entry.content.get("budget_allocation")
            if isinstance(budget, int):
                total += budget
        return total
