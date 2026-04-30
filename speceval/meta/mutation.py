"""Meta-evaluation via mutation testing.

Injects known defects into good specs and verifies the eval catches them.
If a mutation survives (eval doesn't flag it), that's a blind spot.

This is how we harden the eval itself — the RALPH loop.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from speceval.schema import (
    Dimension,
    EvalInput,
    EvalReport,
    GeneratedSpec,
)


@dataclass
class Mutation:
    """A single mutation to inject into a spec."""

    name: str
    description: str
    target_dimension: Dimension
    apply: Callable[[EvalInput], EvalInput]
    expected_drop: float = 0.10  # Minimum score drop expected


@dataclass
class MutationResult:
    """Result of applying a mutation and checking if eval caught it."""

    mutation: Mutation
    baseline_score: float
    mutated_score: float
    caught: bool  # Did the eval detect the defect?
    score_drop: float

    @property
    def survived(self) -> bool:
        return not self.caught


def _mutate_remove_sections(eval_input: EvalInput) -> EvalInput:
    """Remove critical sections from the spec."""
    md = eval_input.generated_spec.markdown
    # Remove everything after "## 6. Gap Analysis" until next section
    md = re.sub(
        r"## \d+\.\s*Gap Analysis.*?(?=## \d+\.|\Z)",
        "",
        md,
        flags=re.DOTALL,
    )
    md = re.sub(
        r"## \d+\.\s*Acceptance Criteria.*?(?=## \d+\.|\Z)",
        "",
        md,
        flags=re.DOTALL,
    )
    new_spec = GeneratedSpec(
        title=eval_input.generated_spec.title,
        markdown=md,
        claims=eval_input.generated_spec.claims,
        sections=[s for s in eval_input.generated_spec.sections
                  if s not in ("Gap Analysis", "Acceptance Criteria")],
    )
    return EvalInput(
        sources=eval_input.sources,
        template=eval_input.template,
        goals=eval_input.goals,
        generated_spec=new_spec,
        reference_spec=eval_input.reference_spec,
    )


def _mutate_vague_requirements(eval_input: EvalInput) -> EvalInput:
    """Replace precise requirements with vague ones."""
    md = eval_input.generated_spec.markdown
    replacements = [
        (r"\bSHALL\b", "should probably"),
        (r"\bMUST\b", "might"),
        (r"≤\d+\s*(?:ms|minutes?|seconds?)", "a reasonable amount of time"),
        (r"≥\d+(?:,\d+)?", "an appropriate number of"),
        (r"\d+%", "a good percentage"),
        (r"p99\s*(?:latency\s*)?≤\s*\d+ms", "acceptable performance"),
    ]
    for pattern, replacement in replacements:
        md = re.sub(pattern, replacement, md)
    new_spec = GeneratedSpec(
        title=eval_input.generated_spec.title,
        markdown=md,
        claims=eval_input.generated_spec.claims,
        sections=eval_input.generated_spec.sections,
    )
    return EvalInput(
        sources=eval_input.sources,
        template=eval_input.template,
        goals=eval_input.goals,
        generated_spec=new_spec,
        reference_spec=eval_input.reference_spec,
    )


def _mutate_remove_citations(eval_input: EvalInput) -> EvalInput:
    """Strip all citations from claims."""
    from speceval.schema import Claim
    new_claims = [
        Claim(
            claim_id=c.claim_id,
            text=c.text,
            section=c.section,
            citations=[],  # Remove all citations
            linked_goal_ids=[],  # Remove goal links
            linked_slot_ids=[],
        )
        for c in eval_input.generated_spec.claims
    ]
    # Also remove citation markers from markdown
    md = re.sub(r"\[Source:.*?\]", "", eval_input.generated_spec.markdown)
    md = re.sub(r"\[Traces to:.*?\]", "", md)
    new_spec = GeneratedSpec(
        title=eval_input.generated_spec.title,
        markdown=md,
        claims=new_claims,
        sections=eval_input.generated_spec.sections,
    )
    return EvalInput(
        sources=eval_input.sources,
        template=eval_input.template,
        goals=eval_input.goals,
        generated_spec=new_spec,
        reference_spec=eval_input.reference_spec,
    )


def _mutate_add_contradictions(eval_input: EvalInput) -> EvalInput:
    """Inject contradictory requirements."""
    md = eval_input.generated_spec.markdown
    contradictions = """
**FR-099:** The system SHALL NOT implement any form of multi-factor authentication.

**FR-100:** The system SHALL maintain session duration of 24 hours minimum.

**FR-101:** The system SHALL use LDAP exclusively and SHALL NOT support SAML or OIDC.
"""
    # Insert contradictions into the requirements section
    md = md.replace(
        "### 7.2 Non-Functional Requirements",
        contradictions + "\n### 7.2 Non-Functional Requirements",
    )
    new_spec = GeneratedSpec(
        title=eval_input.generated_spec.title,
        markdown=md,
        claims=eval_input.generated_spec.claims,
        sections=eval_input.generated_spec.sections,
    )
    return EvalInput(
        sources=eval_input.sources,
        template=eval_input.template,
        goals=eval_input.goals,
        generated_spec=new_spec,
        reference_spec=eval_input.reference_spec,
    )


def _mutate_remove_uncertainty(eval_input: EvalInput) -> EvalInput:
    """Remove all uncertainty markers — make spec falsely certain."""
    md = eval_input.generated_spec.markdown
    # Remove uncertainty markers
    md = re.sub(r"\b(?:TBD|TBC|ASSUMPTION|HUMAN_REQUIRED)\b", "", md, flags=re.IGNORECASE)
    md = re.sub(r"##\s*\d*\.?\s*Assumptions.*?(?=##|\Z)", "", md, flags=re.DOTALL)
    md = re.sub(r"—\s*(?:TBD|pending|to be confirmed).*", "", md, flags=re.IGNORECASE)
    new_spec = GeneratedSpec(
        title=eval_input.generated_spec.title,
        markdown=md,
        claims=eval_input.generated_spec.claims,
        sections=[s for s in eval_input.generated_spec.sections if s != "Assumptions"],
    )
    return EvalInput(
        sources=eval_input.sources,
        template=eval_input.template,
        goals=eval_input.goals,
        generated_spec=new_spec,
        reference_spec=eval_input.reference_spec,
    )


def _mutate_hallucinate_sources(eval_input: EvalInput) -> EvalInput:
    """Add citations to non-existent source files (hallucinated evidence)."""
    from speceval.schema import Claim, Citation as SchemaCitation
    new_claims = []
    for c in eval_input.generated_spec.claims:
        new_citations = list(c.citations) + [
            SchemaCitation(file_path="nonexistent/phantom-doc.pdf", snippet="fabricated evidence"),
            SchemaCitation(file_path="fake/hallucinated-code.java", snippet="imaginary code"),
        ]
        new_claims.append(Claim(
            claim_id=c.claim_id, text=c.text, section=c.section,
            citations=new_citations, linked_goal_ids=c.linked_goal_ids,
            linked_slot_ids=c.linked_slot_ids, confidence=c.confidence,
        ))
    new_spec = GeneratedSpec(
        title=eval_input.generated_spec.title,
        markdown=eval_input.generated_spec.markdown,
        claims=new_claims,
        sections=eval_input.generated_spec.sections,
    )
    return EvalInput(
        sources=eval_input.sources, template=eval_input.template,
        goals=eval_input.goals, generated_spec=new_spec,
        reference_spec=eval_input.reference_spec,
    )


def _mutate_drop_goal_links(eval_input: EvalInput) -> EvalInput:
    """Remove all goal links but keep citations (breaks goal traceability)."""
    from speceval.schema import Claim
    new_claims = [
        Claim(
            claim_id=c.claim_id, text=c.text, section=c.section,
            citations=c.citations, linked_goal_ids=[],
            linked_slot_ids=c.linked_slot_ids, confidence=c.confidence,
        )
        for c in eval_input.generated_spec.claims
    ]
    md = re.sub(r"\[Traces to:.*?\]", "", eval_input.generated_spec.markdown)
    new_spec = GeneratedSpec(
        title=eval_input.generated_spec.title, markdown=md,
        claims=new_claims, sections=eval_input.generated_spec.sections,
    )
    return EvalInput(
        sources=eval_input.sources, template=eval_input.template,
        goals=eval_input.goals, generated_spec=new_spec,
        reference_spec=eval_input.reference_spec,
    )


def _mutate_passive_voice_flood(eval_input: EvalInput) -> EvalInput:
    """Convert active voice requirements to passive voice."""
    md = eval_input.generated_spec.markdown
    replacements = [
        (r"The system SHALL", "It is required that"),
        (r"The system SHALL NOT", "It is not permitted that"),
        (r"the system SHALL", "it is required that"),
    ]
    for pattern, replacement in replacements:
        md = md.replace(pattern, replacement)
    new_spec = GeneratedSpec(
        title=eval_input.generated_spec.title, markdown=md,
        claims=eval_input.generated_spec.claims,
        sections=eval_input.generated_spec.sections,
    )
    return EvalInput(
        sources=eval_input.sources, template=eval_input.template,
        goals=eval_input.goals, generated_spec=new_spec,
        reference_spec=eval_input.reference_spec,
    )


def _mutate_broken_xrefs(eval_input: EvalInput) -> EvalInput:
    """Add broken internal cross-references."""
    md = eval_input.generated_spec.markdown
    broken_links = """
See [Section 99](#nonexistent-section) for details.
As described in [Appendix Z](#appendix-z-missing), the system...
Per [FR-999](#fr-999-phantom), the requirement is...
Reference [Table 42](#table-42-ghost) for configuration options.
"""
    md = md + "\n\n## 13. References\n" + broken_links
    new_spec = GeneratedSpec(
        title=eval_input.generated_spec.title, markdown=md,
        claims=eval_input.generated_spec.claims,
        sections=eval_input.generated_spec.sections,
    )
    return EvalInput(
        sources=eval_input.sources, template=eval_input.template,
        goals=eval_input.goals, generated_spec=new_spec,
        reference_spec=eval_input.reference_spec,
    )


def _mutate_hidden_hedging(eval_input: EvalInput) -> EvalInput:
    """Add hidden uncertainty via hedging language instead of explicit markers."""
    md = eval_input.generated_spec.markdown
    hedges = [
        "\n\nThe migration timeline is probably achievable within the stated period.\n",
        "\nIt seems that the current authentication approach might work for most cases.\n",
        "\nGenerally, the system should be able to handle typical load scenarios.\n",
        "\nIn most cases, the security requirements could be met with standard approaches.\n",
        "\nThe performance targets are believed to be achievable, approximately.\n",
    ]
    # Insert hedging language after the requirements section
    insert_point = md.find("### 7.2")
    if insert_point > 0:
        md = md[:insert_point] + "".join(hedges) + md[insert_point:]
    new_spec = GeneratedSpec(
        title=eval_input.generated_spec.title, markdown=md,
        claims=eval_input.generated_spec.claims,
        sections=eval_input.generated_spec.sections,
    )
    return EvalInput(
        sources=eval_input.sources, template=eval_input.template,
        goals=eval_input.goals, generated_spec=new_spec,
        reference_spec=eval_input.reference_spec,
    )


# Registry of all mutations
MUTATIONS: list[Mutation] = [
    Mutation(
        name="remove_sections",
        description="Remove Gap Analysis and Acceptance Criteria sections",
        target_dimension=Dimension.STRUCTURAL_COMPLETENESS,
        apply=_mutate_remove_sections,
        expected_drop=0.15,
    ),
    Mutation(
        name="vague_requirements",
        description="Replace precise requirements with vague language",
        target_dimension=Dimension.REQUIREMENT_PRECISION,
        apply=_mutate_vague_requirements,
        expected_drop=0.15,
    ),
    Mutation(
        name="remove_citations",
        description="Strip all citations and goal links from claims",
        target_dimension=Dimension.TRACEABILITY,
        apply=_mutate_remove_citations,
        expected_drop=0.20,
    ),
    Mutation(
        name="add_contradictions",
        description="Inject contradictory requirements",
        target_dimension=Dimension.CONSISTENCY,
        apply=_mutate_add_contradictions,
        expected_drop=0.10,
    ),
    Mutation(
        name="remove_uncertainty",
        description="Remove all uncertainty markers and assumptions",
        target_dimension=Dimension.UNCERTAINTY_TRANSPARENCY,
        apply=_mutate_remove_uncertainty,
        expected_drop=0.10,
    ),
    Mutation(
        name="hallucinate_sources",
        description="Add citations to non-existent source files",
        target_dimension=Dimension.TRACEABILITY,
        apply=_mutate_hallucinate_sources,
        expected_drop=0.10,
    ),
    Mutation(
        name="drop_goal_links",
        description="Remove all goal links but keep citations",
        target_dimension=Dimension.TRACEABILITY,
        apply=_mutate_drop_goal_links,
        expected_drop=0.10,
    ),
    Mutation(
        name="passive_voice_flood",
        description="Convert active requirements to passive voice",
        target_dimension=Dimension.REQUIREMENT_PRECISION,
        apply=_mutate_passive_voice_flood,
        expected_drop=0.05,
    ),
    Mutation(
        name="broken_xrefs",
        description="Add broken internal cross-references",
        target_dimension=Dimension.CONSISTENCY,
        apply=_mutate_broken_xrefs,
        expected_drop=0.05,
    ),
    Mutation(
        name="hidden_hedging",
        description="Add hedging language instead of explicit TBD markers",
        target_dimension=Dimension.UNCERTAINTY_TRANSPARENCY,
        apply=_mutate_hidden_hedging,
        expected_drop=0.05,
    ),
]


def run_mutation_suite(
    baseline_input: EvalInput,
    eval_fn: Callable[[EvalInput], EvalReport],
    mutations: list[Mutation] | None = None,
) -> list[MutationResult]:
    """Run all mutations against the baseline and check if eval catches them.

    This is the core of the meta-eval: if a mutation survives,
    the eval has a blind spot that needs fixing.
    """
    mutations = mutations or MUTATIONS
    baseline_report = eval_fn(baseline_input)
    results: list[MutationResult] = []

    for mutation in mutations:
        mutated_input = mutation.apply(baseline_input)
        mutated_report = eval_fn(mutated_input)

        dim = mutation.target_dimension
        baseline_dim_score = (
            baseline_report.dimension_scores[dim].score
            if dim in baseline_report.dimension_scores
            else 0.0
        )
        mutated_dim_score = (
            mutated_report.dimension_scores[dim].score
            if dim in mutated_report.dimension_scores
            else 0.0
        )

        score_drop = baseline_dim_score - mutated_dim_score
        caught = score_drop >= mutation.expected_drop

        results.append(MutationResult(
            mutation=mutation,
            baseline_score=baseline_dim_score,
            mutated_score=mutated_dim_score,
            caught=caught,
            score_drop=score_drop,
        ))

    return results


def mutation_kill_rate(results: list[MutationResult]) -> float:
    """What fraction of mutations were caught by the eval?"""
    if not results:
        return 0.0
    return sum(1 for r in results if r.caught) / len(results)
