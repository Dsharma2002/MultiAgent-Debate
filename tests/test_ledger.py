"""Tests for the Truth Ledger backends and hash-chain integrity."""

import json
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from mad.ledger.memory import InMemoryLedger
from mad.ledger.json_file import JsonFileLedger
from mad.ledger.integrity import verify_chain, detect_tampering, compute_hash
from mad.schemas.evidence import EvidenceEntry


def _make_entry(
    agent_id: str = "test_agent",
    budget: int = 100,
    verified: bool = True,
) -> EvidenceEntry:
    """Helper to create a test evidence entry."""
    return EvidenceEntry(
        author_agent_id=agent_id,
        content={
            "proposal_id": str(uuid4()),
            "budget_allocation": budget,
            "description": f"Test entry by {agent_id}",
        },
        verified_status=verified,
    )


class TestInMemoryLedger:
    """Test the in-memory ledger implementation."""

    def test_append_and_retrieve(self):
        ledger = InMemoryLedger()
        entry = _make_entry()
        committed = ledger.append(entry)

        assert committed.prev_hash == "GENESIS"
        assert committed.entry_hash != ""
        assert ledger.size() == 1

    def test_chain_linkage(self):
        ledger = InMemoryLedger()
        e1 = ledger.append(_make_entry())
        e2 = ledger.append(_make_entry())

        assert e1.prev_hash == "GENESIS"
        assert e2.prev_hash == e1.entry_hash

    def test_get_by_id(self):
        ledger = InMemoryLedger()
        entry = _make_entry()
        committed = ledger.append(entry)

        found = ledger.get(committed.entry_id)
        assert found is not None
        assert found.entry_id == committed.entry_id

    def test_get_nonexistent(self):
        ledger = InMemoryLedger()
        assert ledger.get(uuid4()) is None

    def test_get_latest(self):
        ledger = InMemoryLedger()
        assert ledger.get_latest() is None

        e1 = ledger.append(_make_entry())
        assert ledger.get_latest().entry_id == e1.entry_id

        e2 = ledger.append(_make_entry())
        assert ledger.get_latest().entry_id == e2.entry_id

    def test_get_all_verified_only(self):
        ledger = InMemoryLedger()
        ledger.append(_make_entry(verified=True))
        ledger.append(_make_entry(verified=False))
        ledger.append(_make_entry(verified=True))

        all_entries = ledger.get_all()
        assert len(all_entries) == 3

        verified = ledger.get_all(verified_only=True)
        assert len(verified) == 2

    def test_chain_integrity_valid(self):
        ledger = InMemoryLedger()
        for _ in range(5):
            ledger.append(_make_entry())

        is_valid, errors = ledger.verify_chain_integrity()
        assert is_valid is True
        assert errors == []

    def test_total_budget(self):
        ledger = InMemoryLedger()
        ledger.append(_make_entry(budget=100, verified=True))
        ledger.append(_make_entry(budget=200, verified=True))
        ledger.append(_make_entry(budget=300, verified=False))  # Not verified

        assert ledger.get_total_budget() == 300  # Only verified entries

    def test_snapshot(self):
        ledger = InMemoryLedger()
        for _ in range(3):
            ledger.append(_make_entry())

        snap = ledger.snapshot()
        assert snap.total_entries == 3
        assert snap.chain_valid is True

    def test_empty_ledger_is_valid(self):
        ledger = InMemoryLedger()
        is_valid, errors = ledger.verify_chain_integrity()
        assert is_valid is True
        assert errors == []


class TestJsonFileLedger:
    """Test the JSON file ledger implementation."""

    def test_append_and_persist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_ledger.jsonl"

            # Write entries
            ledger = JsonFileLedger(path)
            e1 = ledger.append(_make_entry())
            e2 = ledger.append(_make_entry())

            assert ledger.size() == 2

            # Reload from file
            ledger2 = JsonFileLedger(path)
            assert ledger2.size() == 2

            entries = ledger2.get_all()
            assert entries[0].entry_id == e1.entry_id
            assert entries[1].entry_id == e2.entry_id

    def test_chain_integrity_after_reload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_ledger.jsonl"

            ledger = JsonFileLedger(path)
            for _ in range(5):
                ledger.append(_make_entry())

            # Reload and verify
            ledger2 = JsonFileLedger(path)
            is_valid, errors = ledger2.verify_chain_integrity()
            assert is_valid is True

    def test_nonexistent_file_creates_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "new_ledger.jsonl"
            ledger = JsonFileLedger(path)
            assert ledger.size() == 0


class TestIntegrity:
    """Test standalone integrity utilities."""

    def test_verify_valid_chain(self):
        ledger = InMemoryLedger()
        for _ in range(5):
            ledger.append(_make_entry())

        entries = ledger.get_all()
        is_valid, errors = verify_chain(entries)
        assert is_valid is True

    def test_detect_tampered_entry(self):
        ledger = InMemoryLedger()
        for _ in range(3):
            ledger.append(_make_entry())

        entries = ledger.get_all()

        # Tamper with middle entry's content
        tampered_entries = list(entries)
        original = tampered_entries[1]
        tampered_entries[1] = EvidenceEntry(
            entry_id=original.entry_id,
            timestamp=original.timestamp,
            author_agent_id=original.author_agent_id,
            content={"proposal_id": str(uuid4()), "budget_allocation": 99999},
            verified_status=original.verified_status,
            prev_hash=original.prev_hash,
            entry_hash=original.entry_hash,  # Old hash — mismatch!
        )

        is_valid, errors = verify_chain(tampered_entries)
        assert is_valid is False

        tampered = detect_tampering(tampered_entries)
        assert len(tampered) >= 1
        assert any(t["index"] == 1 for t in tampered)

    def test_empty_chain_is_valid(self):
        is_valid, errors = verify_chain([])
        assert is_valid is True
        assert errors == []

    def test_compute_hash_deterministic(self):
        data = {"key": "value", "number": 42}
        h1 = compute_hash(data)
        h2 = compute_hash(data)
        assert h1 == h2

    def test_compute_hash_order_independent(self):
        """Hash should be the same regardless of key insertion order."""
        h1 = compute_hash({"b": 2, "a": 1})
        h2 = compute_hash({"a": 1, "b": 2})
        assert h1 == h2
