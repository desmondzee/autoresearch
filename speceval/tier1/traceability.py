"""D5: Traceability — can every claim be traced to a source?

Checks:
- Citation density (what % of claims have citations)
- Citation validity (do cited sources exist in the input set?)
- Goal coverage (do requirements trace to project goals?)
- Slot coverage (are template slots linked to requirements?)
"""

from __future__ import annotations

from speceval.schema import (
    Diagnostic,
    Dimension,
    DimensionScore,
    EvalInput,
    Severity,
)


def evaluate_traceability(eval_input: EvalInput) -> DimensionScore:
    """Evaluate D5: Traceability."""
    spec = eval_input.generated_spec
    sources = eval_input.sources
    goals = eval_input.goals
    template = eval_input.template
    diagnostics: list[Diagnostic] = []
    sub_scores: dict[str, float] = {}

    claims = spec.claims

    if not claims:
        return DimensionScore(
            dimension=Dimension.TRACEABILITY,
            score=0.0,
            details={"error": "No claims found in spec"},
            diagnostics=[Diagnostic(
                dimension=Dimension.TRACEABILITY,
                severity=Severity.CRITICAL,
                message="Spec has no structured claims to trace",
            )],
        )

    # 1. Citation density
    cited = [c for c in claims if c.citations]
    uncited = [c for c in claims if not c.citations]
    citation_density = len(cited) / len(claims)
    sub_scores["citation_density"] = citation_density
    if citation_density < 0.85:
        diagnostics.append(Diagnostic(
            dimension=Dimension.TRACEABILITY,
            severity=Severity.MAJOR,
            message=f"Low citation density: {citation_density:.0%} of claims cite sources (target ≥85%)",
        ))
    for c in uncited[:5]:
        diagnostics.append(Diagnostic(
            dimension=Dimension.TRACEABILITY,
            severity=Severity.MINOR,
            message=f"Uncited claim: '{c.text[:60]}...'",
            location=c.section,
        ))

    # 2. Citation validity
    source_paths = {s.file_path for s in sources}
    total_citations = sum(len(c.citations) for c in claims)
    valid_citations = sum(
        1
        for c in claims
        for cit in c.citations
        if cit.file_path in source_paths
    )
    citation_validity = valid_citations / max(total_citations, 1)
    sub_scores["citation_validity"] = citation_validity
    if citation_validity < 0.95:
        invalid_paths = {
            cit.file_path
            for c in claims
            for cit in c.citations
            if cit.file_path not in source_paths
        }
        for path in list(invalid_paths)[:5]:
            diagnostics.append(Diagnostic(
                dimension=Dimension.TRACEABILITY,
                severity=Severity.MAJOR,
                message=f"Citation references non-existent source: '{path}'",
            ))

    # 3. Goal coverage (if goals provided)
    if goals:
        goal_ids = {g.goal_id for g in goals}
        required_goals = {g.goal_id for g in goals if g.priority in ("REQUIRED", "HIGH")}
        linked_goals = {gid for c in claims for gid in c.linked_goal_ids}
        covered_required = required_goals & linked_goals
        goal_coverage = len(covered_required) / max(len(required_goals), 1)
        sub_scores["goal_coverage"] = goal_coverage
        uncovered = required_goals - linked_goals
        for gid in uncovered:
            goal = next((g for g in goals if g.goal_id == gid), None)
            diagnostics.append(Diagnostic(
                dimension=Dimension.TRACEABILITY,
                severity=Severity.CRITICAL,
                message=f"REQUIRED/HIGH goal not traced to any requirement: '{goal.description[:60] if goal else gid}'",
            ))
    else:
        sub_scores["goal_coverage"] = 1.0  # No goals to check

    # 4. Slot coverage (if template provided)
    if template and template.slots:
        required_slots = {s.slot_id for s in template.slots if s.required}
        linked_slots = {sid for c in claims for sid in c.linked_slot_ids}
        covered_slots = required_slots & linked_slots
        slot_coverage = len(covered_slots) / max(len(required_slots), 1)
        sub_scores["slot_coverage"] = slot_coverage
        uncovered_slots = required_slots - linked_slots
        for sid in uncovered_slots:
            slot = next((s for s in template.slots if s.slot_id == sid), None)
            diagnostics.append(Diagnostic(
                dimension=Dimension.TRACEABILITY,
                severity=Severity.MAJOR,
                message=f"Required template slot not filled: '{slot.section_path if slot else sid}'",
            ))
    else:
        sub_scores["slot_coverage"] = 1.0  # No template to check

    # Composite
    weights = {
        "citation_density": 0.35,
        "citation_validity": 0.25,
        "goal_coverage": 0.25,
        "slot_coverage": 0.15,
    }
    score = sum(weights[k] * sub_scores[k] for k in weights)

    return DimensionScore(
        dimension=Dimension.TRACEABILITY,
        score=score,
        confidence=1.0,
        details={
            "sub_scores": sub_scores,
            "total_claims": len(claims),
            "cited_claims": len(cited),
            "total_citations": total_citations,
            "valid_citations": valid_citations,
        },
        diagnostics=diagnostics,
    )
