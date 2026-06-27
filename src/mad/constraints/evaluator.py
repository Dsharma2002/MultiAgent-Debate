"""
Constraint Evaluator — runs all applicable constraints against an entry.

The evaluator is the enforcement engine: given an EvidenceEntry and the
current ledger state, it checks every constraint that applies to the
authoring agent and returns a consolidated result.
"""

from __future__ import annotations

from mad.constraints.registry import Constraint, ConstraintRegistry, ConstraintResult
from mad.ledger.base import LedgerBackend
from mad.schemas.evidence import EvidenceEntry


class ConstraintEvaluator:
    """
    Evaluates all applicable constraints against a candidate evidence entry.

    Usage:
        evaluator = ConstraintEvaluator(registry)
        result = evaluator.evaluate(entry, ledger)
        if not result.passed:
            print(result.violations)
    """

    def __init__(self, registry: ConstraintRegistry) -> None:
        self._registry = registry

    def evaluate(
        self,
        entry: EvidenceEntry,
        ledger: LedgerBackend,
    ) -> ConstraintResult:
        """
        Evaluate all constraints applicable to the entry's author agent.

        Returns a ConstraintResult with pass/fail status and any violations.
        """
        violations: list[str] = []

        applicable = self._registry.get_for_agent(entry.author_agent_id)

        for constraint in applicable:
            try:
                passed, reason = constraint.rule_fn(entry, ledger)
                if not passed:
                    violation_msg = (
                        f"[{constraint.constraint_id}] {reason or constraint.description}"
                    )
                    violations.append(violation_msg)
            except Exception as e:
                # Constraint evaluation errors are treated as violations
                # (fail-closed approach)
                violations.append(
                    f"[{constraint.constraint_id}] Evaluation error: {e}"
                )

        return ConstraintResult(
            passed=len(violations) == 0,
            violations=violations,
        )

    def evaluate_specific(
        self,
        entry: EvidenceEntry,
        ledger: LedgerBackend,
        constraint_ids: list[str],
    ) -> ConstraintResult:
        """
        Evaluate only the specified constraints (by ID) against an entry.

        This is used by agents during their Audit Mandate — each agent
        cross-audits using only their assigned constraint IDs.
        """
        violations: list[str] = []

        for cid in constraint_ids:
            constraint = self._registry.get(cid)
            if constraint is None:
                violations.append(f"[{cid}] Unknown constraint ID")
                continue

            try:
                passed, reason = constraint.rule_fn(entry, ledger)
                if not passed:
                    violation_msg = f"[{cid}] {reason or constraint.description}"
                    violations.append(violation_msg)
            except Exception as e:
                violations.append(f"[{cid}] Evaluation error: {e}")

        return ConstraintResult(
            passed=len(violations) == 0,
            violations=violations,
        )
