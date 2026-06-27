"""
Hash-chain integrity utilities.

Provides standalone functions for computing hashes and verifying
the integrity of ledger entry chains without needing a full backend.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from mad.schemas.evidence import EvidenceEntry, _canonical_json


def compute_hash(data: dict[str, Any]) -> str:
    """
    Compute SHA-256 hash of a canonical JSON representation.

    The data dict is serialized with sorted keys and minimal whitespace
    to ensure deterministic hashing regardless of insertion order.
    """
    canonical = _canonical_json(data)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_chain(entries: list[EvidenceEntry]) -> tuple[bool, list[str]]:
    """
    Verify the complete hash-chain integrity of a list of entries.

    Checks:
    1. Genesis linkage — first entry must have prev_hash='GENESIS'
    2. Chain continuity — each entry's prev_hash == prior entry's entry_hash
    3. Self-integrity — each entry's stored hash matches its recomputed hash

    Returns:
        (is_valid, list_of_error_messages)
    """
    errors: list[str] = []

    if not entries:
        return True, []

    # Check genesis
    first = entries[0]
    if first.prev_hash != "GENESIS":
        errors.append(
            f"First entry ({first.entry_id}) should have prev_hash='GENESIS', "
            f"got '{first.prev_hash}'"
        )

    for i, entry in enumerate(entries):
        # Self-hash verification
        recomputed = entry.recompute_hash()
        if entry.entry_hash != recomputed:
            errors.append(
                f"Entry {i} ({entry.entry_id}): hash mismatch. "
                f"Stored: {entry.entry_hash[:16]}..., "
                f"Recomputed: {recomputed[:16]}..."
            )

        # Chain linkage (entries after the first)
        if i > 0:
            expected_prev = entries[i - 1].entry_hash
            if entry.prev_hash != expected_prev:
                errors.append(
                    f"Entry {i} ({entry.entry_id}): chain break. "
                    f"Expected prev_hash={expected_prev[:16]}..., "
                    f"got={entry.prev_hash[:16]}..."
                )

    return len(errors) == 0, errors


def detect_tampering(
    entries: list[EvidenceEntry],
) -> list[dict[str, Any]]:
    """
    Detect specific entries that appear to have been tampered with.

    Returns a list of dicts describing each tampered entry with:
    - index: position in the chain
    - entry_id: the entry's UUID
    - issue: description of the problem
    """
    tampered: list[dict[str, Any]] = []

    for i, entry in enumerate(entries):
        issues: list[str] = []

        # Check self-hash
        if not entry.verify_integrity():
            issues.append("content-hash-mismatch")

        # Check chain link
        if i == 0 and entry.prev_hash != "GENESIS":
            issues.append("invalid-genesis")
        elif i > 0 and entry.prev_hash != entries[i - 1].entry_hash:
            issues.append("chain-link-broken")

        if issues:
            tampered.append(
                {
                    "index": i,
                    "entry_id": str(entry.entry_id),
                    "issues": issues,
                }
            )

    return tampered
