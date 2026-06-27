"""
Security Auditor Agent — specializes in threat modeling and access control.

Core Specialty (70%): Threat modeling, vulnerability checking, access control.
Audit Mandate (30%): Cross-audits using Constraint_02 (security boundaries).
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from mad.agents.base import BaseAgent, register_agent
from mad.ledger.base import LedgerBackend
from mad.schemas.evidence import EvidenceEntry


@register_agent("security_auditor")
class SecurityAuditorAgent(BaseAgent):
    """
    Agent specializing in security analysis and threat assessment.

    Evaluates proposals for security vulnerabilities, data privacy
    concerns, and access control requirements.
    """

    # Keywords that indicate security-sensitive content
    SECURITY_KEYWORDS = {
        "authentication", "authorization", "password", "token", "secret",
        "encryption", "pii", "personal data", "credit card", "ssn",
        "api key", "private key", "certificate", "oauth", "jwt",
        "session", "cookie", "csrf", "xss", "injection", "sql",
    }

    def core_execute(
        self,
        context: dict[str, Any],
        ledger: LedgerBackend,
    ) -> EvidenceEntry:
        """
        Generate a security assessment with threat model and recommendations.
        """
        proposal_id = context.get("proposal_id", str(uuid4()))
        description = context.get("description", "")
        budget = context.get("budget_allocation", 0)

        # Security analysis
        threats = self._identify_threats(context, ledger)
        security_class = self._classify_security_level(context)
        recommendations = self._generate_recommendations(context, threats)

        content: dict[str, Any] = {
            "proposal_id": proposal_id,
            "tech_feasibility_score": context.get("tech_feasibility_score", 0.5),
            "budget_allocation": budget,
            "description": f"[Security Assessment] {description}",
            "assessment_type": "security_audit",
            "security_classification": security_class,
            "identified_threats": threats,
            "security_recommendations": recommendations,
        }

        if "metadata" in context:
            content["metadata"] = context["metadata"]

        return EvidenceEntry(
            author_agent_id=self.agent_id,
            content=content,
            verified_status=False,
        )

    def _identify_threats(
        self,
        context: dict[str, Any],
        ledger: LedgerBackend,
    ) -> list[str]:
        """Identify potential security threats from the proposal."""
        threats: list[str] = []

        description = str(context.get("description", "")).lower()

        # Check for security-sensitive topics
        found_keywords = [
            kw for kw in self.SECURITY_KEYWORDS if kw in description
        ]

        if found_keywords:
            threats.append(
                f"Security-sensitive topics detected: {', '.join(found_keywords)}"
            )

        # Check for data handling
        if any(kw in description for kw in ("database", "storage", "persist")):
            threats.append("Data persistence — verify encryption at rest")

        if any(kw in description for kw in ("api", "endpoint", "http", "request")):
            threats.append("Network exposure — verify authentication and rate limiting")

        # Check ledger for prior security concerns
        verified = ledger.get_all(verified_only=True)
        security_entries = [
            e for e in verified
            if e.content.get("assessment_type") == "security_audit"
        ]
        if security_entries:
            threats.append(
                f"Prior security assessments exist ({len(security_entries)}) — "
                f"verify consistency with previous findings"
            )

        if not threats:
            threats.append("No immediate threats identified — standard security review applies")

        return threats

    def _classify_security_level(self, context: dict[str, Any]) -> str:
        """Classify the security level of the proposal."""
        description = str(context.get("description", "")).lower()

        # Check explicit classification
        explicit = context.get("security_classification")
        if explicit:
            return explicit

        # Infer from content
        high_risk_keywords = {"pii", "personal data", "credit card", "ssn", "password", "secret"}
        medium_risk_keywords = {"authentication", "authorization", "api key", "token"}

        if any(kw in description for kw in high_risk_keywords):
            return "high"
        elif any(kw in description for kw in medium_risk_keywords):
            return "medium"
        return "standard"

    def _generate_recommendations(
        self,
        context: dict[str, Any],
        threats: list[str],
    ) -> list[str]:
        """Generate security recommendations based on identified threats."""
        recs: list[str] = []

        if any("encryption" in t.lower() or "data persistence" in t.lower() for t in threats):
            recs.append("Implement AES-256 encryption at rest for all sensitive data")

        if any("network" in t.lower() or "api" in t.lower() for t in threats):
            recs.append("Enforce TLS 1.3 for all network communications")
            recs.append("Implement API rate limiting and input validation")

        if any("authentication" in t.lower() for t in threats):
            recs.append("Use industry-standard authentication (OAuth 2.0 / OIDC)")

        # Default recommendations
        recs.extend([
            "Conduct dependency vulnerability scan before deployment",
            "Implement comprehensive audit logging",
        ])

        return recs

    def _domain_audit(
        self,
        entry: EvidenceEntry,
        ledger: LedgerBackend,
    ) -> list[str]:
        """Security audit: check for privacy violations and data exposure risks."""
        issues: list[str] = []

        content = entry.content
        description = str(content.get("description", "")).lower()

        # Check if non-security agents are handling security-sensitive content
        if entry.author_agent_id != self.agent_id:
            found_sensitive = [
                kw for kw in self.SECURITY_KEYWORDS if kw in description
            ]
            if found_sensitive:
                issues.append(
                    f"Non-security agent '{entry.author_agent_id}' handling "
                    f"security-sensitive content (keywords: {', '.join(found_sensitive)}). "
                    f"Requires security review."
                )

        # Check for missing security classification on sensitive entries
        if content.get("security_classification") in ("high", "critical"):
            if not content.get("security_recommendations"):
                issues.append(
                    "High-security entry lacks security_recommendations"
                )

        return issues
