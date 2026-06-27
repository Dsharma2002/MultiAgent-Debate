"""
JSON-file persistent ledger implementation.

Stores entries in a JSONL (JSON Lines) file for durability across process restarts.
Each line is a single JSON-serialized EvidenceEntry.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from uuid import UUID

from mad.ledger.base import LedgerBackend
from mad.ledger.memory import _verify_chain
from mad.schemas.evidence import EvidenceEntry


class JsonFileLedger(LedgerBackend):
    """
    Append-only ledger backed by a JSONL file.

    On initialization, loads any existing entries from the file.
    New entries are appended atomically (write + flush).
    """

    def __init__(self, file_path: str | Path) -> None:
        self._path = Path(file_path)
        self._entries: list[EvidenceEntry] = []
        self._index: dict[UUID, int] = {}
        self._lock = threading.Lock()

        # Load existing entries from file
        if self._path.exists():
            self._load_from_file()

    def _load_from_file(self) -> None:
        """Load entries from the JSONL file."""
        with open(self._path, "r") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entry = EvidenceEntry(**data)
                    self._entries.append(entry)
                    self._index[entry.entry_id] = len(self._entries) - 1
                except (json.JSONDecodeError, ValueError) as e:
                    raise ValueError(
                        f"Failed to parse ledger entry at line {line_num}: {e}"
                    ) from e

    def _append_to_file(self, entry: EvidenceEntry) -> None:
        """Append a single entry to the JSONL file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a") as f:
            f.write(entry.model_dump_json() + "\n")
            f.flush()

    def append(self, entry: EvidenceEntry) -> EvidenceEntry:
        """Append an entry, persisting to the file."""
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

            # Persist to file BEFORE adding to memory (crash safety)
            self._append_to_file(committed)

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
        """Retrieve all entries."""
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
        """Verify the hash chain integrity."""
        with self._lock:
            return _verify_chain(self._entries)

    def size(self) -> int:
        """Return the number of entries."""
        with self._lock:
            return len(self._entries)
