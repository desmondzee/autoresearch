"""D1: Structural Completeness — are all required sections present?

Checks the generated spec's Markdown structure against a configurable
section checklist. Architecture-agnostic: works with any spec that
uses Markdown headings.
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

# Default required sections for a modernisation PRD
DEFAULT_REQUIRED_SECTIONS: list[str] = [
    "purpose",
    "scope",
    "stakeholders",
    "glossary",
    "legacy system",
    "gap analysis",
    "requirements",
    "acceptance criteria",
    "constraints",
    "dependencies",
    "assumptions",
    "risks",
]

# Critical sections — missing any of these triggers a hard penalty
CRITICAL_SECTIONS: set[str] = {
    "requirements",
    "acceptance criteria",
    "gap analysis",
    "scope",
    "purpose",
}

# Patterns that indicate section presence (case-insensitive substring)
SECTION_ALIASES: dict[str, list[str]] = {
    "purpose": ["purpose", "objective", "mission", "overview", "introduction"],
    "scope": ["scope", "boundaries", "in scope", "out of scope"],
    "stakeholders": ["stakeholder", "audience", "users", "actors", "roles"],
    "glossary": ["glossary", "definitions", "terminology", "acronyms"],
    "requirements": ["requirement", "functional", "non-functional", "feature", "capability"],
    "acceptance criteria": ["acceptance", "criteria", "definition of done", "done when"],
    "constraints": ["constraint", "limitation", "restriction"],
    "dependencies": ["dependenc", "prerequisite", "integration"],
    "assumptions": ["assumption", "presupposition"],
    "risks": ["risk", "mitigation", "threat", "failure mode"],
    "legacy system": ["legacy", "current system", "existing system", "as-is"],
    "gap analysis": ["gap", "divergence", "delta", "difference"],
}


def _extract_headings(markdown: str) -> list[str]:
    """Extract all Markdown headings from text."""
    pattern = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
    return [m.group(1).strip() for m in pattern.finditer(markdown)]


def _section_present(headings: list[str], section: str) -> bool:
    """Check if a required section is present (fuzzy match via aliases)."""
    aliases = SECTION_ALIASES.get(section, [section])
    headings_lower = [h.lower() for h in headings]
    return any(
        any(alias in heading for heading in headings_lower)
        for alias in aliases
    )


@dataclass
class StructuralConfig:
    """Configuration for structural completeness check."""

    required_sections: list[str] = field(
        default_factory=lambda: list(DEFAULT_REQUIRED_SECTIONS)
    )
    min_heading_count: int = 5
    min_word_count: int = 200
    max_empty_section_ratio: float = 0.10


def evaluate_structural_completeness(
    eval_input: EvalInput,
    config: StructuralConfig | None = None,
) -> DimensionScore:
    """Evaluate D1: Structural Completeness."""
    config = config or StructuralConfig()
    markdown = eval_input.generated_spec.markdown
    diagnostics: list[Diagnostic] = []
    sub_scores: dict[str, float] = {}

    # 1. Section presence
    headings = _extract_headings(markdown)
    present = []
    missing = []
    for section in config.required_sections:
        if _section_present(headings, section):
            present.append(section)
        else:
            missing.append(section)
            diagnostics.append(Diagnostic(
                dimension=Dimension.STRUCTURAL_COMPLETENESS,
                severity=Severity.MAJOR,
                message=f"Required section missing: '{section}'",
            ))

    section_ratio = len(present) / max(len(config.required_sections), 1)
    # Non-linear penalty: missing ANY critical section drops score sharply
    section_score = section_ratio ** 2 if section_ratio < 1.0 else 1.0
    # Additional hard penalty per missing critical section
    missing_critical = [s for s in missing if s in CRITICAL_SECTIONS]
    critical_penalty = len(missing_critical) * 0.15
    section_score = max(0.0, section_score - critical_penalty)
    sub_scores["section_coverage"] = section_score

    # 2. Heading density
    heading_score = min(1.0, len(headings) / config.min_heading_count)
    sub_scores["heading_density"] = heading_score
    if len(headings) < config.min_heading_count:
        diagnostics.append(Diagnostic(
            dimension=Dimension.STRUCTURAL_COMPLETENESS,
            severity=Severity.MINOR,
            message=f"Only {len(headings)} headings found (minimum {config.min_heading_count})",
        ))

    # 3. Content volume
    words = len(markdown.split())
    word_score = min(1.0, words / config.min_word_count)
    sub_scores["content_volume"] = word_score
    if words < config.min_word_count:
        diagnostics.append(Diagnostic(
            dimension=Dimension.STRUCTURAL_COMPLETENESS,
            severity=Severity.MAJOR,
            message=f"Spec has only {words} words (minimum {config.min_word_count})",
        ))

    # 4. Empty sections detection
    sections_content = re.split(r"^#{1,6}\s+.+$", markdown, flags=re.MULTILINE)
    empty_count = sum(
        1 for s in sections_content[1:]  # Skip content before first heading
        if len(s.strip()) < 20
    )
    total_sections = max(len(sections_content) - 1, 1)
    empty_ratio = empty_count / total_sections
    empty_score = max(0.0, 1.0 - (empty_ratio / config.max_empty_section_ratio))
    sub_scores["non_empty_sections"] = min(1.0, empty_score)
    if empty_ratio > config.max_empty_section_ratio:
        diagnostics.append(Diagnostic(
            dimension=Dimension.STRUCTURAL_COMPLETENESS,
            severity=Severity.MAJOR,
            message=f"{empty_count}/{total_sections} sections are empty ({empty_ratio:.0%})",
        ))

    # Composite: weighted average of sub-scores
    weights = {
        "section_coverage": 0.60,
        "heading_density": 0.10,
        "content_volume": 0.15,
        "non_empty_sections": 0.15,
    }
    score = sum(weights[k] * sub_scores[k] for k in weights)

    return DimensionScore(
        dimension=Dimension.STRUCTURAL_COMPLETENESS,
        score=score,
        confidence=1.0,  # Deterministic — full confidence
        details={"sub_scores": sub_scores, "headings": headings, "missing_sections": missing},
        diagnostics=diagnostics,
    )
