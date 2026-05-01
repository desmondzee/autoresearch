"""D8: Uncertainty Transparency — does the spec flag what it doesn't know?

Checks:
- Explicit uncertainty markers (TBD, assumption, to be confirmed)
- HUMAN_REQUIRED escalation patterns
- Hedging language analysis
- Missing-info sections
"""

from __future__ import annotations

import re

from speceval.schema import (
    Diagnostic,
    Dimension,
    DimensionScore,
    EvalInput,
    Severity,
)

# Explicit uncertainty markers (good — spec is being honest)
UNCERTAINTY_MARKERS = [
    "TBD", "TBC", "to be determined", "to be confirmed",
    "to be decided", "to be agreed", "assumption",
    "assumed", "open question", "unknown",
    "HUMAN_REQUIRED", "human required", "needs clarification",
    "pending decision", "out of scope for now",
    "not yet defined", "subject to change",
    "requires further analysis", "needs investigation",
    "placeholder", "draft", "tentative",
]

# Hedging language (bad — spec is uncertain but not flagging it)
HIDDEN_UNCERTAINTY = [
    "probably", "possibly", "perhaps", "might",
    "could be", "may or may not", "it depends",
    "generally", "typically", "usually", "often",
    "in most cases", "as far as we know",
    "to some extent", "more or less",
    "roughly", "approximately", "around",
    "it seems", "appears to be", "believed to be",
]


def evaluate_uncertainty_transparency(eval_input: EvalInput) -> DimensionScore:
    """Evaluate D8: Uncertainty Transparency."""
    markdown = eval_input.generated_spec.markdown
    diagnostics: list[Diagnostic] = []
    sub_scores: dict[str, float] = {}

    sentences = [s.strip() for s in re.split(r"[.!?\n]", markdown) if len(s.strip()) > 10]
    total = max(len(sentences), 1)

    # 1. Explicit uncertainty markers (presence is GOOD)
    explicit_hits = []
    for marker in UNCERTAINTY_MARKERS:
        for s in sentences:
            if re.search(rf"\b{re.escape(marker)}\b", s, re.IGNORECASE):
                explicit_hits.append((marker, s[:80]))

    # Score: having some explicit markers is good (shows honesty)
    # Having none in a complex spec is suspicious
    has_sources = len(eval_input.sources) > 0
    if has_sources and not explicit_hits:
        sub_scores["explicit_flagging"] = 0.3  # Suspicious — no uncertainty at all?
        diagnostics.append(Diagnostic(
            dimension=Dimension.UNCERTAINTY_TRANSPARENCY,
            severity=Severity.MAJOR,
            message="No explicit uncertainty markers found — is the spec truly 100% certain?",
        ))
    elif len(explicit_hits) > 0:
        # Good — some uncertainty is flagged
        sub_scores["explicit_flagging"] = min(1.0, 0.5 + len(explicit_hits) * 0.1)
    else:
        sub_scores["explicit_flagging"] = 0.7  # No sources, so maybe fine

    # 2. Hidden uncertainty (presence is BAD — uncertain but not flagging)
    hidden_hits = []
    for hedge in HIDDEN_UNCERTAINTY:
        for s in sentences:
            if re.search(rf"\b{re.escape(hedge)}\b", s, re.IGNORECASE):
                hidden_hits.append((hedge, s[:80]))

    hidden_ratio = len(hidden_hits) / total
    hidden_score = max(0.0, 1.0 - hidden_ratio * 10)
    sub_scores["no_hidden_uncertainty"] = hidden_score
    for hedge, context in hidden_hits[:5]:
        diagnostics.append(Diagnostic(
            dimension=Dimension.UNCERTAINTY_TRANSPARENCY,
            severity=Severity.MINOR,
            message=f"Hedging language '{hedge}' — should this be an explicit TBD/assumption?",
            evidence=context,
        ))

    # 3. HUMAN_REQUIRED pattern (axiom A6 compliance)
    human_required_count = len(re.findall(
        r"\bHUMAN[_\s]REQUIRED\b", markdown, re.IGNORECASE
    ))
    if has_sources:
        # Having at least some HUMAN_REQUIRED flags is expected
        hr_score = min(1.0, 0.5 + human_required_count * 0.25)
    else:
        hr_score = 1.0
    sub_scores["human_required_pattern"] = hr_score

    # 4. Assumptions section check
    has_assumptions_section = bool(re.search(
        r"^#{1,6}\s+.*(?:assumption|open question|unresolved)",
        markdown,
        re.IGNORECASE | re.MULTILINE,
    ))
    sub_scores["assumptions_section"] = 1.0 if has_assumptions_section else 0.5

    # Composite
    weights = {
        "explicit_flagging": 0.35,
        "no_hidden_uncertainty": 0.30,
        "human_required_pattern": 0.20,
        "assumptions_section": 0.15,
    }
    score = sum(weights[k] * sub_scores[k] for k in weights)

    return DimensionScore(
        dimension=Dimension.UNCERTAINTY_TRANSPARENCY,
        score=score,
        confidence=1.0,
        details={
            "sub_scores": sub_scores,
            "explicit_markers_found": len(explicit_hits),
            "hidden_uncertainty_found": len(hidden_hits),
            "human_required_count": human_required_count,
        },
        diagnostics=diagnostics,
    )
