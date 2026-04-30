"""Synthetic test fixtures for calibration and meta-evaluation.

Provides known-good and known-bad specs to verify the eval catches
real defects and doesn't penalise good specs.

Fixture design inspired by mutation testing: each bad fixture has
a specific injected defect that the eval MUST catch.
"""

from __future__ import annotations

from speceval.schema import (
    Citation,
    Claim,
    EvalInput,
    GeneratedSpec,
    ProjectGoal,
    SourceDocument,
    SpecTemplate,
    TemplateSlot,
)


def _make_source_docs() -> list[SourceDocument]:
    """Standard source document set for all fixtures."""
    return [
        SourceDocument(
            file_path="legacy/auth-service.java",
            content="""
public class AuthService {
    // Legacy LDAP-based authentication service
    // Handles 50,000 users across 12 government departments
    // Last modified: 2018-03-15
    // Known issues: no MFA, session timeout hardcoded to 8 hours

    public AuthResult authenticate(String username, String password) {
        LDAPConnection conn = getLDAPConnection();
        return conn.bind(username, password);
    }

    public void logout(String sessionId) {
        sessionStore.remove(sessionId);
    }
}
""",
            doc_type="CODE",
            temporal_tag="PAST",
        ),
        SourceDocument(
            file_path="docs/system-overview.md",
            content="""
# Authentication System Overview

The current system uses LDAP for authentication with Active Directory.
Session management is handled via in-memory session store (Redis cluster).
No multi-factor authentication is implemented.
Password policy requires 8+ characters, no complexity requirements.
The system serves 12 government departments with approximately 50,000 users.
Peak login volume: 5,000 concurrent sessions during morning rush (9-10 AM).
99.5% uptime over the past 12 months.
""",
            doc_type="DOC",
            temporal_tag="PRESENT",
        ),
        SourceDocument(
            file_path="policy/security-baseline-2025.md",
            content="""
# Government Security Baseline 2025

All authentication systems MUST implement multi-factor authentication (MFA).
Password policies MUST enforce: minimum 12 characters, complexity requirements.
Session timeouts MUST NOT exceed 30 minutes for sensitive operations.
All authentication events MUST be logged with tamper-evident audit trail.
Systems MUST support SAML 2.0 and OpenID Connect for federation.
""",
            doc_type="POLICY",
            temporal_tag="POLICY",
        ),
    ]


def _make_goals() -> list[ProjectGoal]:
    """Standard project goals for all fixtures."""
    return [
        ProjectGoal(
            goal_id="G1",
            description="Implement multi-factor authentication for all users",
            priority="REQUIRED",
            success_criteria=["MFA enabled for 100% of users", "Support TOTP and WebAuthn"],
        ),
        ProjectGoal(
            goal_id="G2",
            description="Achieve compliance with Government Security Baseline 2025",
            priority="REQUIRED",
            success_criteria=["All MUST requirements in security baseline satisfied"],
        ),
        ProjectGoal(
            goal_id="G3",
            description="Reduce session timeout to 30 minutes",
            priority="HIGH",
            success_criteria=["Session timeout configurable", "Default ≤ 30 minutes"],
        ),
        ProjectGoal(
            goal_id="G4",
            description="Support federated identity via SAML 2.0 and OIDC",
            priority="MEDIUM",
            success_criteria=["SAML 2.0 IdP integration tested", "OIDC provider configured"],
        ),
    ]


def _make_template() -> SpecTemplate:
    """Standard modernisation template."""
    return SpecTemplate(
        name="Government System Modernisation Template",
        content="# Modernisation Specification Template",
        slots=[
            TemplateSlot("S1", "Purpose", "Describe the purpose of this modernisation", required=True),
            TemplateSlot("S2", "Scope", "Define system boundaries", required=True),
            TemplateSlot("S3", "Legacy System Description", "Document current system", required=True),
            TemplateSlot("S4", "Gap Analysis", "Identify gaps between current and target", required=True),
            TemplateSlot("S5", "Requirements", "List functional and non-functional requirements", required=True),
            TemplateSlot("S6", "Acceptance Criteria", "Define acceptance criteria", required=True),
            TemplateSlot("S7", "Risks and Mitigations", "Identify risks", required=False),
        ],
    )


def make_good_spec() -> EvalInput:
    """A well-written modernisation spec that should score high across all dimensions."""
    markdown = """# Authentication System Modernisation Specification

## 1. Purpose

This specification defines the modernisation of the government authentication
service from LDAP-based authentication to a modern identity platform supporting
multi-factor authentication (MFA), federated identity, and enhanced audit
capabilities, in compliance with Government Security Baseline 2025.

## 2. Scope

### 2.1 In Scope
- Authentication service modernisation (LDAP → OIDC/SAML 2.0)
- Multi-factor authentication implementation (TOTP, WebAuthn)
- Session management hardening (configurable timeouts, ≤30 minutes default)
- Audit trail implementation (tamper-evident, Ed25519-signed)
- Password policy enforcement (12+ characters, complexity requirements)

### 2.2 Out of Scope
- User provisioning workflows (handled by HR system integration — TBD)
- Network infrastructure changes
- Client application modifications (beyond auth redirect)

## 3. Stakeholders

| Role | Department | Authority |
|---|---|---|
| CISO | Security Office | Final approval on security architecture |
| System Owner | IT Operations | Operational sign-off |
| Users | 12 departments | Acceptance testing |

## 4. Glossary

- **MFA** — Multi-Factor Authentication. Requires two or more verification factors.
- **TOTP** — Time-based One-Time Password. RFC 6238 standard.
- **WebAuthn** — Web Authentication API. W3C standard for passwordless auth.
- **OIDC** — OpenID Connect. Identity layer on OAuth 2.0.

## 5. Legacy System Description

The current authentication system uses LDAP with Active Directory backend.
[Source: legacy/auth-service.java, docs/system-overview.md]

**Current capabilities:**
- Basic username/password authentication via LDAP bind
- In-memory session store (Redis cluster)
- Serves 50,000 users across 12 government departments
- Peak: 5,000 concurrent sessions (9-10 AM)
- 99.5% uptime over past 12 months

**Known deficiencies:**
- No multi-factor authentication [Source: docs/system-overview.md]
- Session timeout hardcoded to 8 hours [Source: legacy/auth-service.java]
- Password policy: only 8+ characters, no complexity [Source: docs/system-overview.md]
- No federated identity support

## 6. Gap Analysis

| Gap ID | Category | Legacy State | Target State | Priority | Evidence |
|---|---|---|---|---|---|
| GAP-001 | MISSING | No MFA | MFA for all users | REQUIRED | [policy/security-baseline-2025.md] |
| GAP-002 | CHANGED | 8-hour session timeout | ≤30 min timeout | HIGH | [policy/security-baseline-2025.md] |
| GAP-003 | MISSING | No federation | SAML 2.0 + OIDC | MEDIUM | [policy/security-baseline-2025.md] |
| GAP-004 | CHANGED | 8-char passwords | 12-char + complexity | REQUIRED | [policy/security-baseline-2025.md] |
| GAP-005 | MISSING | No audit trail | Tamper-evident audit | REQUIRED | [policy/security-baseline-2025.md] |

## 7. Requirements

### 7.1 Functional Requirements

**FR-001:** The system SHALL implement multi-factor authentication using TOTP
(RFC 6238) and WebAuthn (W3C) for all user accounts.
[Traces to: G1, GAP-001]

**FR-002:** The system SHALL enforce session timeouts of ≤30 minutes for
sensitive operations, configurable per department.
[Traces to: G3, GAP-002]

**FR-003:** The system SHALL support SAML 2.0 IdP integration and OpenID
Connect provider configuration for federated identity.
[Traces to: G4, GAP-003]

**FR-004:** The system SHALL enforce password policies requiring minimum
12 characters with uppercase, lowercase, numeric, and special character
requirements.
[Traces to: G2, GAP-004]

**FR-005:** The system SHALL log all authentication events with tamper-evident
audit trail using Ed25519 signatures.
[Traces to: G2, GAP-005]

### 7.2 Non-Functional Requirements

**NFR-001:** The system SHALL support ≥5,000 concurrent authenticated sessions
with p99 authentication latency ≤500ms.

**NFR-002:** The system SHALL maintain ≥99.9% uptime (measured monthly).

**NFR-003:** The system SHALL complete MFA challenge within 2 seconds p99.

## 8. Acceptance Criteria

- [ ] MFA enabled for 100% of user accounts
- [ ] TOTP and WebAuthn both functional in staging environment
- [ ] Session timeout defaults to 30 minutes, configurable per department
- [ ] Password policy enforced on all new and changed passwords
- [ ] Audit trail tamper-evidence verified by independent security review
- [ ] SAML 2.0 integration tested with 3 federated IdPs
- [ ] Load test: 5,000 concurrent sessions, p99 latency ≤500ms

## 9. Constraints

- MUST use existing Active Directory as user store (no migration in scope)
- MUST maintain backward compatibility with legacy session tokens during transition
- Budget: £2.1M over 18 months

## 10. Dependencies

- Active Directory availability for user store
- HSM availability for Ed25519 key management
- Identity provider (ASSUMPTION: Azure AD — TBD confirmation from CISO)

## 11. Assumptions

- **ASSUMPTION:** Azure AD will be the primary IdP — PENDING CISO confirmation
- **ASSUMPTION:** WebAuthn hardware tokens budget approved — TBD procurement
- **ASSUMPTION:** Legacy applications can be updated to redirect to new auth endpoint within 3 months

## 12. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Legacy app incompatibility with OIDC redirect | Medium | High | Maintain LDAP bridge during transition |
| User resistance to MFA | Medium | Medium | Phased rollout with training programme |
| HSM procurement delays | Low | High | Software key fallback (reduced security — HUMAN_REQUIRED) |
"""
    claims = [
        Claim("FR-001", "The system SHALL implement MFA using TOTP and WebAuthn",
              "Requirements", [Citation("policy/security-baseline-2025.md", snippet="MUST implement MFA")],
              linked_goal_ids=["G1"], linked_slot_ids=["S5"]),
        Claim("FR-002", "The system SHALL enforce session timeouts ≤30 minutes",
              "Requirements", [Citation("policy/security-baseline-2025.md", snippet="MUST NOT exceed 30 minutes")],
              linked_goal_ids=["G3"], linked_slot_ids=["S5"]),
        Claim("FR-003", "The system SHALL support SAML 2.0 and OIDC",
              "Requirements", [Citation("policy/security-baseline-2025.md", snippet="MUST support SAML 2.0 and OIDC")],
              linked_goal_ids=["G4"], linked_slot_ids=["S5"]),
        Claim("FR-004", "The system SHALL enforce 12-char password policy",
              "Requirements", [Citation("policy/security-baseline-2025.md", snippet="minimum 12 characters")],
              linked_goal_ids=["G2"], linked_slot_ids=["S5"]),
        Claim("FR-005", "The system SHALL log all auth events with tamper-evident audit",
              "Requirements", [Citation("policy/security-baseline-2025.md", snippet="tamper-evident audit trail")],
              linked_goal_ids=["G2"], linked_slot_ids=["S5"]),
        Claim("NFR-001", "The system SHALL support ≥5,000 concurrent sessions p99 ≤500ms",
              "Requirements", [Citation("docs/system-overview.md", snippet="5,000 concurrent sessions")],
              linked_slot_ids=["S5"]),
        Claim("SCOPE-001", "Purpose and scope of modernisation",
              "Purpose", linked_slot_ids=["S1", "S2"]),
        Claim("LEGACY-001", "Legacy system description",
              "Legacy System Description", [Citation("legacy/auth-service.java"), Citation("docs/system-overview.md")],
              linked_slot_ids=["S3"]),
        Claim("GAP-001", "Gap analysis covering 5 gaps",
              "Gap Analysis", [Citation("policy/security-baseline-2025.md")],
              linked_slot_ids=["S4"]),
        Claim("AC-001", "Acceptance criteria defined",
              "Acceptance Criteria", linked_slot_ids=["S6"]),
    ]

    return EvalInput(
        sources=_make_source_docs(),
        template=_make_template(),
        goals=_make_goals(),
        generated_spec=GeneratedSpec(
            title="Authentication System Modernisation Specification",
            markdown=markdown,
            claims=claims,
            sections=["Purpose", "Scope", "Stakeholders", "Glossary",
                       "Legacy System Description", "Gap Analysis", "Requirements",
                       "Acceptance Criteria", "Constraints", "Dependencies",
                       "Assumptions", "Risks"],
        ),
    )


def make_bad_spec_missing_sections() -> EvalInput:
    """Bad spec: missing critical sections (should fail D1)."""
    markdown = """# Auth Modernisation

## Requirements

The system should be modernised to support MFA and better security.
It needs to be fast and scalable.
The implementation should be user-friendly and robust.
"""
    return EvalInput(
        sources=_make_source_docs(),
        template=_make_template(),
        goals=_make_goals(),
        generated_spec=GeneratedSpec(
            title="Auth Modernisation",
            markdown=markdown,
            claims=[],
            sections=["Requirements"],
        ),
    )


def make_bad_spec_vague_requirements() -> EvalInput:
    """Bad spec: vague, untestable requirements (should fail D2)."""
    markdown = """# Authentication System Modernisation

## Purpose
Modernise the authentication system to be more modern and efficient.

## Scope
The scope covers various authentication improvements as needed.

## Requirements

- The system should be fast and responsive
- Authentication should be seamless and user-friendly
- The system should be scalable and robust
- Security should be improved as appropriate
- The system should handle various user scenarios efficiently
- Performance should be adequate for typical usage
- The implementation should be simple and maintainable
- The system should support modern authentication methods

## Acceptance Criteria
- System works properly
- Users are satisfied with the experience
- Security is improved
"""
    return EvalInput(
        sources=_make_source_docs(),
        template=_make_template(),
        goals=_make_goals(),
        generated_spec=GeneratedSpec(
            title="Authentication System Modernisation",
            markdown=markdown,
            claims=[],
            sections=["Purpose", "Scope", "Requirements", "Acceptance Criteria"],
        ),
    )


def make_bad_spec_no_traceability() -> EvalInput:
    """Bad spec: no citations or goal links (should fail D5)."""
    markdown = """# Authentication System Modernisation Specification

## Purpose
Modernise the authentication service.

## Scope
Authentication system upgrade.

## Stakeholders
IT department and security office.

## Requirements

**FR-001:** The system SHALL implement multi-factor authentication.

**FR-002:** The system SHALL enforce session timeouts of 30 minutes.

**FR-003:** The system SHALL support SAML 2.0.

**FR-004:** The system SHALL enforce strong password policies.

## Acceptance Criteria
- MFA works
- Sessions time out correctly
"""
    claims = [
        Claim("FR-001", "SHALL implement MFA", "Requirements"),  # No citations, no goals
        Claim("FR-002", "SHALL enforce 30-min timeouts", "Requirements"),
        Claim("FR-003", "SHALL support SAML 2.0", "Requirements"),
        Claim("FR-004", "SHALL enforce strong passwords", "Requirements"),
    ]
    return EvalInput(
        sources=_make_source_docs(),
        template=_make_template(),
        goals=_make_goals(),
        generated_spec=GeneratedSpec(
            title="Auth Modernisation",
            markdown=markdown,
            claims=claims,
            sections=["Purpose", "Scope", "Stakeholders", "Requirements", "Acceptance Criteria"],
        ),
    )


def make_bad_spec_contradictions() -> EvalInput:
    """Bad spec: internal contradictions (should fail D6)."""
    markdown = """# Authentication System Modernisation

## Purpose
Modernise the authentication service.

## Scope
In scope: LDAP replacement. Out of scope: authentication changes.

## Requirements

**FR-001:** The system SHALL enforce session timeouts of 30 minutes.

**FR-002:** The system SHALL maintain session duration of 8 hours for user convenience.

**FR-003:** The system SHALL NOT support federated identity protocols.

**FR-004:** The system SHALL implement SAML 2.0 and OpenID Connect federation.

**FR-005:** The system SHALL use LDAP authentication exclusively.

**FR-006:** The system SHALL migrate away from LDAP to modern protocols.

## Glossary
- **MFA** — Multi-Factor Authentication. A security measure.
- **MFA** — Manual Failure Analysis. A testing technique.

## Acceptance Criteria
- System uses LDAP only
- System supports OIDC federation
"""
    return EvalInput(
        sources=_make_source_docs(),
        template=_make_template(),
        goals=_make_goals(),
        generated_spec=GeneratedSpec(
            title="Auth Modernisation",
            markdown=markdown,
            claims=[],
            sections=["Purpose", "Scope", "Requirements", "Glossary", "Acceptance Criteria"],
        ),
    )


def make_bad_spec_no_uncertainty() -> EvalInput:
    """Bad spec: no uncertainty acknowledgment (should fail D8)."""
    markdown = """# Authentication System Modernisation

## Purpose
This specification comprehensively covers all aspects of the modernisation.

## Scope
Complete replacement of authentication infrastructure.

## Requirements

**FR-001:** The system SHALL implement MFA using Azure AD as the identity provider.

**FR-002:** The system SHALL complete deployment in exactly 6 months.

**FR-003:** The system SHALL require zero downtime during migration.

**FR-004:** The system SHALL support all legacy applications without any changes.

**FR-005:** The system SHALL achieve 100% user adoption on day one.

## Constraints
There are no significant constraints or risks.

## Dependencies
The system has no external dependencies.

## Acceptance Criteria
Everything works perfectly on first deployment.
"""
    return EvalInput(
        sources=_make_source_docs(),
        template=_make_template(),
        goals=_make_goals(),
        generated_spec=GeneratedSpec(
            title="Auth Modernisation",
            markdown=markdown,
            claims=[],
            sections=["Purpose", "Scope", "Requirements", "Constraints",
                       "Dependencies", "Acceptance Criteria"],
        ),
    )
