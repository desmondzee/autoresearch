"""D2: Requirement Precision — are requirements unambiguous and testable?

Checks for:
- RFC 2119 keyword usage (SHALL/SHOULD/MAY)
- EARS syntax compliance (Easy Approach to Requirements Syntax)
- Vague/ambiguous term detection
- Passive voice overuse
- Measurability (numeric targets, testable assertions)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from speceval.schema import (
    Diagnostic,
    Dimension,
    DimensionScore,
    EvalInput,
    Severity,
)

# RFC 2119 keywords
RFC2119_KEYWORDS = {
    "SHALL", "SHALL NOT", "MUST", "MUST NOT", "REQUIRED",
    "SHOULD", "SHOULD NOT", "RECOMMENDED",
    "MAY", "OPTIONAL",
}

# EARS patterns (Easy Approach to Requirements Syntax)
EARS_PATTERNS = [
    # Ubiquitous: "The <system> shall <action>"
    re.compile(r"\b(?:shall|must|will)\b\s+\w+", re.IGNORECASE),
    # Event-driven: "When <trigger>, the <system> shall <action>"
    re.compile(r"\bwhen\b\s+.+?,\s+(?:the\s+)?\w+\s+(?:shall|must|will)\b", re.IGNORECASE),
    # Unwanted behaviour: "If <condition>, then the <system> shall <action>"
    re.compile(r"\bif\b\s+.+?,\s+(?:then\s+)?(?:the\s+)?\w+\s+(?:shall|must|will)\b", re.IGNORECASE),
    # State-driven: "While <state>, the <system> shall <action>"
    re.compile(r"\bwhile\b\s+.+?,\s+(?:the\s+)?\w+\s+(?:shall|must|will)\b", re.IGNORECASE),
]

# Vague/ambiguous terms that weaken requirements
VAGUE_TERMS = [
    "appropriate", "adequate", "as needed", "as required",
    "best effort", "easy", "efficient", "fast", "flexible",
    "friendly", "good", "improved", "intuitive", "lightweight",
    "minimal", "modern", "nice", "optimal", "performant",
    "proper", "quick", "reasonable", "robust", "scalable",
    "seamless", "simple", "smart", "smooth", "soon",
    "state of the art", "sufficient", "suitable", "timely",
    "user-friendly", "various", "etc", "and so on",
    "among others", "as appropriate", "as applicable",
    "normal", "typical", "standard", "general",
]

# Passive voice indicators
PASSIVE_INDICATORS = [
    re.compile(r"\b(?:is|are|was|were|be|been|being)\s+\w+ed\b", re.IGNORECASE),
    re.compile(r"\b(?:is|are|was|were|be|been|being)\s+\w+en\b", re.IGNORECASE),
]

# Measurability indicators (numeric targets)
MEASURABLE_PATTERNS = [
    re.compile(r"\b\d+\s*(?:ms|seconds?|minutes?|hours?|days?|%|percent|MB|GB|TB|KB)\b", re.IGNORECASE),
    re.compile(r"(?:≥|>=|≤|<=|>|<)\s*\d+", re.IGNORECASE),
    re.compile(r"\b(?:at least|at most|no more than|no fewer than|within|maximum|minimum)\s+\d+", re.IGNORECASE),
    re.compile(r"\b\d+(?:\.\d+)?(?:x|×)\b", re.IGNORECASE),
]


def _extract_requirement_sentences(markdown: str) -> list[str]:
    """Extract sentences that look like requirements (contain RFC 2119 keywords or imperative verbs)."""
    sentences = re.split(r"[.!?\n]", markdown)
    reqs = []
    for s in sentences:
        s = s.strip()
        if len(s) < 10:
            continue
        # Check for RFC 2119 keywords or imperative patterns
        if any(kw.lower() in s.lower() for kw in RFC2119_KEYWORDS):
            reqs.append(s)
        elif re.search(r"\b(?:the system|the platform|the service|it)\s+(?:shall|must|will|should)\b", s, re.IGNORECASE):
            reqs.append(s)
    return reqs


@dataclass
class PrecisionConfig:
    """Configuration for requirement precision checks."""

    vague_terms: list[str] = field(default_factory=lambda: list(VAGUE_TERMS))
    max_passive_ratio: float = 0.20
    min_measurable_ratio: float = 0.30
    min_rfc2119_ratio: float = 0.50


def evaluate_requirement_precision(
    eval_input: EvalInput,
    config: PrecisionConfig | None = None,
) -> DimensionScore:
    """Evaluate D2: Requirement Precision."""
    config = config or PrecisionConfig()
    markdown = eval_input.generated_spec.markdown
    diagnostics: list[Diagnostic] = []
    sub_scores: dict[str, float] = {}

    sentences = re.split(r"[.!?\n]", markdown)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    req_sentences = _extract_requirement_sentences(markdown)

    if not sentences:
        return DimensionScore(
            dimension=Dimension.REQUIREMENT_PRECISION,
            score=0.0,
            details={"error": "No sentences found"},
            diagnostics=[Diagnostic(
                dimension=Dimension.REQUIREMENT_PRECISION,
                severity=Severity.CRITICAL,
                message="Spec contains no parseable sentences",
            )],
        )

    # 1. RFC 2119 keyword usage
    rfc_count = sum(
        1 for s in sentences
        if any(kw.lower() in s.lower() for kw in RFC2119_KEYWORDS)
    )
    rfc_ratio = rfc_count / len(sentences)
    rfc_score = min(1.0, rfc_ratio / config.min_rfc2119_ratio) if config.min_rfc2119_ratio > 0 else 1.0
    sub_scores["rfc2119_usage"] = rfc_score
    if rfc_ratio < config.min_rfc2119_ratio * 0.5:
        diagnostics.append(Diagnostic(
            dimension=Dimension.REQUIREMENT_PRECISION,
            severity=Severity.MAJOR,
            message=f"Low RFC 2119 keyword usage: {rfc_ratio:.0%} (target ≥{config.min_rfc2119_ratio:.0%})",
        ))

    # 2. EARS compliance
    ears_matches = sum(
        1 for s in req_sentences
        if any(p.search(s) for p in EARS_PATTERNS)
    )
    ears_ratio = ears_matches / max(len(req_sentences), 1)
    sub_scores["ears_compliance"] = ears_ratio

    # 3. Vague term detection
    vague_hits: list[tuple[str, str]] = []
    for s in sentences:
        for term in config.vague_terms:
            if re.search(rf"\b{re.escape(term)}\b", s, re.IGNORECASE):
                vague_hits.append((term, s[:80]))
    vague_ratio = len(vague_hits) / max(len(sentences), 1)
    vague_score = max(0.0, 1.0 - vague_ratio * 5)  # Penalise heavily
    sub_scores["low_ambiguity"] = vague_score
    for term, context in vague_hits[:10]:  # Cap diagnostics
        diagnostics.append(Diagnostic(
            dimension=Dimension.REQUIREMENT_PRECISION,
            severity=Severity.MINOR,
            message=f"Vague term '{term}' found",
            evidence=context,
        ))

    # 4. Passive voice detection
    passive_count = sum(
        1 for s in sentences
        if any(p.search(s) for p in PASSIVE_INDICATORS)
    )
    passive_ratio = passive_count / max(len(sentences), 1)
    passive_score = max(0.0, 1.0 - (passive_ratio / config.max_passive_ratio))
    sub_scores["active_voice"] = min(1.0, passive_score)

    # 5. Measurability
    measurable_count = sum(
        1 for s in req_sentences
        if any(p.search(s) for p in MEASURABLE_PATTERNS)
    )
    measurable_ratio = measurable_count / max(len(req_sentences), 1)
    measurable_score = min(1.0, measurable_ratio / config.min_measurable_ratio) if config.min_measurable_ratio > 0 else 1.0
    sub_scores["measurability"] = measurable_score

    # Composite
    weights = {
        "rfc2119_usage": 0.25,
        "ears_compliance": 0.20,
        "low_ambiguity": 0.25,
        "active_voice": 0.10,
        "measurability": 0.20,
    }
    score = sum(weights[k] * sub_scores[k] for k in weights)

    return DimensionScore(
        dimension=Dimension.REQUIREMENT_PRECISION,
        score=score,
        confidence=1.0,
        details={
            "sub_scores": sub_scores,
            "total_sentences": len(sentences),
            "requirement_sentences": len(req_sentences),
            "vague_hit_count": len(vague_hits),
            "passive_ratio": passive_ratio,
        },
        diagnostics=diagnostics,
    )
