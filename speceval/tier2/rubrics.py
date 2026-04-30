"""Rubric definitions for all 8 dimensions.

Each rubric is a standalone scoring prompt designed to avoid criterion
conflation (per Autorubric guidance). Rubrics are architecture-agnostic.
"""

from __future__ import annotations

from speceval.schema import Dimension

# Per-dimension rubric prompts for LLM-as-judge evaluation
RUBRICS: dict[Dimension, str] = {
    Dimension.STRUCTURAL_COMPLETENESS: """## Evaluation: Structural Completeness (D1)

You are evaluating a modernisation specification for structural completeness.

**Score 1-5:**
- 5: All expected sections present and well-structured. Clear hierarchy. Table of contents matches content. Every section has substantive content.
- 4: Most sections present. One or two minor sections missing or sparse. Good structure overall.
- 3: Core sections present but several supporting sections missing. Structure is passable but incomplete.
- 2: Major sections missing (e.g., no acceptance criteria, no stakeholders, no constraints). Disorganised.
- 1: Minimal structure. Reads like unstructured prose rather than a specification.

**Output format:** { "score": <1-5>, "reasoning": "<2-3 sentences>" }
Do NOT reward length alone. A short but complete spec beats a long but disorganised one.""",

    Dimension.REQUIREMENT_PRECISION: """## Evaluation: Requirement Precision (D2)

You are evaluating individual requirements in this specification for precision and testability.

**Score 1-5:**
- 5: Requirements use RFC 2119 keywords correctly. Every requirement is testable with a concrete acceptance criterion. No vague language. Active voice throughout.
- 4: Most requirements are precise and testable. Minor instances of vague language that don't materially affect implementability.
- 3: Mix of precise and vague requirements. Some are testable, others use language like "should be fast" or "user-friendly" without quantification.
- 2: Most requirements are vague or untestable. Overuse of passive voice and ambiguous terms.
- 1: Requirements are wishes, not specifications. No testable criteria. Language is entirely qualitative.

**Output format:** { "score": <1-5>, "reasoning": "<2-3 sentences>" }""",

    Dimension.LEGACY_FIDELITY: """## Evaluation: Legacy Fidelity (D3)

You are evaluating how faithfully this modernisation specification captures the existing system's behaviour.

**Context:** You will receive SOURCE DOCUMENTS describing the legacy system and the GENERATED SPECIFICATION.

**Score 1-5:**
- 5: Every significant legacy behaviour documented in source material is accurately reflected in the spec. No misrepresentations. Clear distinction between "current state" and "target state".
- 4: Most legacy behaviours captured. Minor omissions that don't affect implementation. Good current-vs-target separation.
- 3: Key legacy behaviours captured but several are missed or misrepresented. Some confusion between current and target state.
- 2: Significant legacy behaviours missing or misrepresented. Spec reads more like a green-field PRD than a modernisation spec.
- 1: Legacy system behaviour is largely ignored or fabricated. Spec does not reflect the source material.

**Output format:** { "score": <1-5>, "reasoning": "<2-3 sentences>" }""",

    Dimension.GAP_COVERAGE: """## Evaluation: Gap Coverage (D4)

You are evaluating how well this specification identifies and categorises gaps between the legacy system and the modernisation target.

**Context:** You will receive SOURCE DOCUMENTS, TARGET GOALS, and the GENERATED SPECIFICATION.

**Score 1-5:**
- 5: Every gap between legacy and target is identified, categorised (missing/new/changed), and supported by evidence from source docs. Gap analysis is systematic and exhaustive.
- 4: Most gaps identified and categorised. Minor omissions in evidence or categorisation. Good overall coverage.
- 3: Key gaps identified but categorisation is incomplete or evidence is sparse. Some gaps are noted but not analysed.
- 2: Some gaps mentioned but many are missed. No systematic gap analysis. Important discrepancies overlooked.
- 1: No meaningful gap analysis. Spec reads as a generic PRD with no awareness of what changed vs. what stayed.

**Output format:** { "score": <1-5>, "reasoning": "<2-3 sentences>" }""",

    Dimension.TRACEABILITY: """## Evaluation: Traceability (D5)

You are evaluating whether requirements in this specification can be traced to their sources and forward to project goals.

**Score 1-5:**
- 5: Every requirement cites its source (document, interview, code). Every project goal is addressed by at least one requirement. Bidirectional traceability is clear.
- 4: Most requirements cite sources. Most goals are addressed. Minor gaps in the trace chain.
- 3: Some requirements cite sources but many don't. Goal coverage is partial. Traceability is present but inconsistent.
- 2: Few citations. Goals are mentioned but not systematically linked to requirements. Traceability is weak.
- 1: No citations or source references. Goals are disconnected from requirements. No traceability.

**Output format:** { "score": <1-5>, "reasoning": "<2-3 sentences>" }""",

    Dimension.CONSISTENCY: """## Evaluation: Consistency (D6)

You are evaluating this specification for internal contradictions, conflicting requirements, and terminology consistency.

**Score 1-5:**
- 5: No contradictions. Terminology is used consistently throughout. All cross-references resolve. Requirements are mutually compatible.
- 4: No significant contradictions. Minor terminology inconsistencies that don't cause confusion.
- 3: One or two contradictions that could cause implementation confusion. Some terminology drift between sections.
- 2: Multiple contradictions. Terminology is inconsistent. Some requirements directly conflict with others.
- 1: Pervasive contradictions. Different sections describe incompatible systems. Terminology is chaotic.

**Output format:** { "score": <1-5>, "reasoning": "<2-3 sentences>" }""",

    Dimension.DECISION_READINESS: """## Evaluation: Decision Readiness (D7)

You are evaluating whether a non-technical decision-maker could use this specification to make informed choices.

**Score 1-5:**
- 5: Spec presents options with evidence for each. Trade-offs are explicit. A decision-maker can choose → edit → sign without needing to read code. Executive summary is clear.
- 4: Most decisions are well-framed. Minor areas where technical depth overwhelms decision context. Good but not perfect for non-technical review.
- 3: Some decisions are well-framed but others require significant technical knowledge. Mixed accessibility.
- 2: Spec is primarily technical. Decision-makers would struggle to extract actionable choices. Few options presented.
- 1: Spec is impenetrable for non-technical stakeholders. No decision framework. Reads like an engineering design doc, not a decision document.

**Output format:** { "score": <1-5>, "reasoning": "<2-3 sentences>" }""",

    Dimension.UNCERTAINTY_TRANSPARENCY: """## Evaluation: Uncertainty Transparency (D8)

You are evaluating whether this specification honestly flags what it doesn't know.

**Score 1-5:**
- 5: Every assumption is explicitly labelled. Unknown areas are marked TBD with a clear path to resolution. HUMAN_REQUIRED flags are used where appropriate. No false confidence.
- 4: Most uncertainties are flagged. Minor areas of hidden assumption. Good overall transparency.
- 3: Some uncertainties flagged but others are buried or implied. Mix of honest flagging and silent uncertainty.
- 2: Few uncertainties acknowledged. Spec presents uncertain information as fact. Some hedging language without explicit TBD markers.
- 1: No uncertainty acknowledged. Spec claims total certainty despite gaps in source material. Likely hallucinated content.

**Output format:** { "score": <1-5>, "reasoning": "<2-3 sentences>" }""",
}


def build_judge_prompt(
    dimension: Dimension,
    spec_markdown: str,
    source_summaries: list[str] | None = None,
    goals: list[str] | None = None,
) -> str:
    """Build the complete judge prompt for a single dimension."""
    rubric = RUBRICS[dimension]
    parts = [rubric, "\n---\n"]

    if source_summaries and dimension in (
        Dimension.LEGACY_FIDELITY,
        Dimension.GAP_COVERAGE,
        Dimension.TRACEABILITY,
    ):
        parts.append("## SOURCE DOCUMENTS (summaries)\n")
        for i, summary in enumerate(source_summaries[:10], 1):
            parts.append(f"### Source {i}\n{summary[:2000]}\n")

    if goals and dimension in (
        Dimension.GAP_COVERAGE,
        Dimension.TRACEABILITY,
    ):
        parts.append("## TARGET GOALS\n")
        for goal in goals[:20]:
            parts.append(f"- {goal}\n")

    parts.append(f"## GENERATED SPECIFICATION\n\n{spec_markdown[:15000]}")

    return "\n".join(parts)
