"""
Verification Gate — the enforcement point for the Behavioral Protocol.

Every state update must pass through this gate before being committed
to the Truth Ledger. The gate implements a strict verification sequence:

1. Vocabulary Check — all keys conform to Shared Vocabulary
2. Constraint Check — all applicable constraints are satisfied
3. Peer Audit — other agents cross-audit the draft (min N approvals)
4. Decision — REJECT (with error feedback) or COMMIT to ledger
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from mad.agents.base import BaseAgent, AuditResult
from mad.constraints.evaluator import ConstraintEvaluator
from mad.constraints.registry import ConstraintRegistry
from mad.ledger.base import LedgerBackend
from mad.schemas.evidence import EvidenceEntry
from mad.schemas.vocabulary import VocabularyRegistry

logger = logging.getLogger(__name__)


@dataclass
class GateResult:
    """Result of passing an entry through the Verification Gate."""

    committed: bool
    entry: EvidenceEntry | None = None
    errors: list[str] = field(default_factory=list)
    audit_results: list[AuditResult] = field(default_factory=list)
    peer_validation_count: int = 0

    def __str__(self) -> str:
        if self.committed:
            return (
                f"COMMITTED: Entry {self.entry.entry_id if self.entry else 'N/A'} "
                f"with {self.peer_validation_count} peer validations"
            )
        return f"REJECTED: {len(self.errors)} error(s) — {'; '.join(self.errors[:3])}"


class VerificationGate:
    """
    The central verification point for the Behavioral Protocol.

    No data enters the Shared Evidence ledger without passing
    through this gate. Implements a fail-closed approach:
    any error means rejection.
    """

    def __init__(
        self,
        vocabulary: VocabularyRegistry,
        constraint_registry: ConstraintRegistry,
        ledger: LedgerBackend,
        min_peer_validations: int = 2,
    ) -> None:
        self._vocabulary = vocabulary
        self._constraint_evaluator = ConstraintEvaluator(constraint_registry)
        self._ledger = ledger
        self._min_peer_validations = min_peer_validations

    def verify(
        self,
        draft: EvidenceEntry,
        peer_agents: list[BaseAgent],
    ) -> GateResult:
        """
        Run the full verification pipeline on a draft entry.

        Steps:
        1. Vocabulary Check
        2. Constraint Check
        3. Peer Audit
        4. Decision (COMMIT or REJECT)

        Args:
            draft: The draft EvidenceEntry to verify
            peer_agents: Other agents that will cross-audit this entry

        Returns:
            GateResult with committed status, entry, and any errors
        """
        errors: list[str] = []
        audit_results: list[AuditResult] = []

        # ── Step 1: Vocabulary Check ──────────────────────────────────────
        logger.info(
            f"[Gate] Step 1: Vocabulary check for entry by '{draft.author_agent_id}'"
        )
        vocab_errors = self._vocabulary.validate_data(draft.content)
        if vocab_errors:
            for err in vocab_errors:
                errors.append(f"[Vocabulary] {err}")
            logger.warning(f"[Gate] Vocabulary check FAILED: {vocab_errors}")

        # ── Step 2: Constraint Check ──────────────────────────────────────
        logger.info(f"[Gate] Step 2: Constraint check")
        constraint_result = self._constraint_evaluator.evaluate(
            entry=draft, ledger=self._ledger
        )
        if not constraint_result.passed:
            errors.extend(constraint_result.violations)
            logger.warning(
                f"[Gate] Constraint check FAILED: {constraint_result.violations}"
            )

        # If vocabulary or constraints failed, reject immediately
        # (no point doing peer audit on structurally invalid data)
        if errors:
            logger.info(f"[Gate] Early rejection — structural issues found")
            return GateResult(
                committed=False,
                entry=draft,
                errors=errors,
                audit_results=[],
                peer_validation_count=0,
            )

        # ── Step 3: Peer Audit ────────────────────────────────────────────
        logger.info(
            f"[Gate] Step 3: Peer audit "
            f"(need {self._min_peer_validations} approvals from "
            f"{len(peer_agents)} peers)"
        )
        approval_count = 0

        for peer in peer_agents:
            # Skip self-audit (an agent cannot audit its own entry)
            if peer.agent_id == draft.author_agent_id:
                continue

            result = peer.audit(draft, self._ledger)
            audit_results.append(result)

            if result.approved:
                approval_count += 1
                logger.info(f"[Gate] Peer '{peer.agent_id}' APPROVED")
            else:
                logger.info(
                    f"[Gate] Peer '{peer.agent_id}' REJECTED: "
                    f"{result.rejection_reasons}"
                )
                # Collect rejection reasons as errors
                for reason in result.rejection_reasons:
                    errors.append(
                        f"[Peer Audit: {peer.agent_id}] {reason}"
                    )

        # Check minimum peer validation threshold
        if approval_count < self._min_peer_validations:
            errors.append(
                f"[Peer Validation] Insufficient approvals: "
                f"{approval_count}/{self._min_peer_validations} required"
            )

        # ── Step 4: Decision ──────────────────────────────────────────────
        if errors:
            logger.info(
                f"[Gate] REJECTED with {len(errors)} error(s), "
                f"{approval_count} peer approvals"
            )
            return GateResult(
                committed=False,
                entry=draft,
                errors=errors,
                audit_results=audit_results,
                peer_validation_count=approval_count,
            )

        # COMMIT: Create verified entry with peer validation count and commit
        logger.info(f"[Gate] APPROVED — committing to ledger")

        # Add peer validation count to content
        verified_content = dict(draft.content)
        verified_content["peer_validations"] = approval_count

        # Get the latest entry's hash for chaining
        latest = self._ledger.get_latest()
        prev_hash = latest.entry_hash if latest else "GENESIS"

        # Create the verified entry
        verified_entry = EvidenceEntry(
            entry_id=draft.entry_id,
            timestamp=draft.timestamp,
            author_agent_id=draft.author_agent_id,
            content=verified_content,
            verified_status=True,
            prev_hash=prev_hash,
            rejection_history=draft.rejection_history,
        )

        # Commit to ledger
        committed_entry = self._ledger.append(verified_entry)

        logger.info(
            f"[Gate] COMMITTED entry {committed_entry.entry_id} "
            f"(hash: {committed_entry.entry_hash[:16]}...)"
        )

        return GateResult(
            committed=True,
            entry=committed_entry,
            errors=[],
            audit_results=audit_results,
            peer_validation_count=approval_count,
        )
