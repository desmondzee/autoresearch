"""Core I/O schema for the speceval benchmark.

Eval Contract:
  INPUT:  EvalInput (source docs + template + goals + generated spec)
  OUTPUT: EvalReport (per-dimension scores + composite + diagnostics)

This is architecture-agnostic — any agentic spec generation pipeline
can be benchmarked by producing the required output format.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Dimension(str, Enum):
    """The 8 quality dimensions for modernisation spec evaluation."""

    STRUCTURAL_COMPLETENESS = "D1_structural_completeness"
    REQUIREMENT_PRECISION = "D2_requirement_precision"
    LEGACY_FIDELITY = "D3_legacy_fidelity"
    GAP_COVERAGE = "D4_gap_coverage"
    TRACEABILITY = "D5_traceability"
    CONSISTENCY = "D6_consistency"
    DECISION_READINESS = "D7_decision_readiness"
    UNCERTAINTY_TRANSPARENCY = "D8_uncertainty_transparency"


class Severity(str, Enum):
    """Defect severity for diagnostics."""

    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


@dataclass
class SourceDocument:
    """A single source document ingested by the pipeline."""

    file_path: str
    content: str
    doc_type: str = "UNKNOWN"  # CODE | DOC | POLICY | TRACE | INTERVIEW
    temporal_tag: str = "PRESENT"  # PAST | PRESENT | FUTURE | POLICY

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.content.encode()).hexdigest()[:16]


@dataclass
class TemplateSlot:
    """A slot in the spec template that must be filled."""

    slot_id: str
    section_path: str
    prompt: str
    required: bool = True
    expected_kind: str = "markdown"  # string | paragraph | markdown | table


@dataclass
class SpecTemplate:
    """The target template defining the contract for 'spec done'."""

    name: str
    content: str
    slots: list[TemplateSlot] = field(default_factory=list)


@dataclass
class ProjectGoal:
    """A modernisation goal with success criteria."""

    goal_id: str
    description: str
    priority: str = "REQUIRED"  # REQUIRED | HIGH | MEDIUM | LOW
    success_criteria: list[str] = field(default_factory=list)


@dataclass
class Citation:
    """A citation linking a claim to source evidence."""

    file_path: str
    section_header: str | None = None
    snippet: str = ""
    byte_offset_start: int = 0
    byte_offset_end: int = 0

    def is_valid(self, sources: list[SourceDocument]) -> bool:
        """Check if this citation resolves to a real source."""
        return any(s.file_path == self.file_path for s in sources)


@dataclass
class Claim:
    """A single requirement/claim in the generated spec."""

    claim_id: str
    text: str
    section: str
    citations: list[Citation] = field(default_factory=list)
    linked_goal_ids: list[str] = field(default_factory=list)
    linked_slot_ids: list[str] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class GeneratedSpec:
    """The output of the agentic spec generation pipeline."""

    title: str
    markdown: str
    claims: list[Claim] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.markdown.encode()).hexdigest()[:16]


@dataclass
class EvalInput:
    """Everything needed to evaluate a generated spec.

    This is the benchmark's input contract. Any pipeline that can
    produce these artifacts can be benchmarked.
    """

    sources: list[SourceDocument]
    template: SpecTemplate | None = None
    goals: list[ProjectGoal] = field(default_factory=list)
    generated_spec: GeneratedSpec = field(default_factory=lambda: GeneratedSpec(
        title="", markdown=""
    ))
    reference_spec: GeneratedSpec | None = None  # Gold standard for ref-based eval

    @property
    def input_hash(self) -> str:
        """Deterministic hash for caching/idempotency."""
        canonical = json.dumps({
            "sources": [s.content_hash for s in self.sources],
            "template": self.template.name if self.template else None,
            "goals": [g.goal_id for g in self.goals],
            "spec": self.generated_spec.content_hash,
        }, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]


@dataclass
class Diagnostic:
    """A single finding from the evaluation."""

    dimension: Dimension
    severity: Severity
    message: str
    location: str | None = None  # section/line reference
    evidence: str | None = None  # supporting snippet


@dataclass
class DimensionScore:
    """Score for a single quality dimension."""

    dimension: Dimension
    score: float  # 0.0 - 1.0
    confidence: float = 1.0  # How confident is this score
    details: dict[str, Any] = field(default_factory=dict)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def pass_threshold(self) -> float:
        """Default pass thresholds per dimension."""
        thresholds = {
            Dimension.STRUCTURAL_COMPLETENESS: 0.95,
            Dimension.REQUIREMENT_PRECISION: 0.80,
            Dimension.LEGACY_FIDELITY: 0.80,
            Dimension.GAP_COVERAGE: 0.80,
            Dimension.TRACEABILITY: 0.85,
            Dimension.CONSISTENCY: 0.80,
            Dimension.DECISION_READINESS: 0.70,
            Dimension.UNCERTAINTY_TRANSPARENCY: 0.70,
        }
        return thresholds.get(self.dimension, 0.70)

    @property
    def passed(self) -> bool:
        return self.score >= self.pass_threshold


# Default dimension weights for composite scoring
DEFAULT_WEIGHTS: dict[Dimension, float] = {
    Dimension.STRUCTURAL_COMPLETENESS: 0.10,
    Dimension.REQUIREMENT_PRECISION: 0.15,
    Dimension.LEGACY_FIDELITY: 0.20,
    Dimension.GAP_COVERAGE: 0.15,
    Dimension.TRACEABILITY: 0.15,
    Dimension.CONSISTENCY: 0.10,
    Dimension.DECISION_READINESS: 0.10,
    Dimension.UNCERTAINTY_TRANSPARENCY: 0.05,
}


@dataclass
class EvalReport:
    """Complete evaluation report — the benchmark's output contract."""

    input_hash: str
    dimension_scores: dict[Dimension, DimensionScore] = field(default_factory=dict)
    weights: dict[Dimension, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    diagnostics: list[Diagnostic] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def composite_score(self) -> float:
        """Weighted composite across all dimensions."""
        if not self.dimension_scores:
            return 0.0
        total = 0.0
        weight_sum = 0.0
        for dim, score in self.dimension_scores.items():
            w = self.weights.get(dim, 0.0)
            total += w * score.score
            weight_sum += w
        return total / weight_sum if weight_sum > 0 else 0.0

    @property
    def all_passed(self) -> bool:
        return all(s.passed for s in self.dimension_scores.values())

    @property
    def passed_count(self) -> int:
        return sum(1 for s in self.dimension_scores.values() if s.passed)

    @property
    def total_count(self) -> int:
        return len(self.dimension_scores)

    def summary_line(self) -> str:
        return (
            f"composite={self.composite_score:.3f} "
            f"passed={self.passed_count}/{self.total_count} "
            f"diagnostics={len(self.diagnostics)}"
        )
