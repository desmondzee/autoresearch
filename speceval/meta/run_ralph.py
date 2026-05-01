"""RALPH loop runner — Research, Assess, Learn, Plan, Harden.

Run: python -m speceval.meta.run_ralph

This is the meta-evaluation entry point. It:
1. Loads the good spec fixture as baseline
2. Runs all mutations against the eval
3. Reports kill rate and surviving mutations
4. Identifies blind spots for the next improvement cycle
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from speceval.fixtures.synthetic import (
    make_bad_spec_contradictions,
    make_bad_spec_missing_sections,
    make_bad_spec_no_traceability,
    make_bad_spec_no_uncertainty,
    make_bad_spec_vague_requirements,
    make_good_spec,
)
from speceval.meta.mutation import (
    MUTATIONS,
    MutationResult,
    mutation_kill_rate,
    run_mutation_suite,
)
from speceval.runner import RunConfig, run_full_eval
from speceval.schema import EvalInput, EvalReport


def _eval_fn(eval_input: EvalInput) -> EvalReport:
    """Standard eval function for meta-evaluation."""
    config = RunConfig(run_tier1=True, run_tier2=False)
    return run_full_eval(eval_input, config)


def _run_fixture_validation() -> list[tuple[str, bool, float]]:
    """Validate that known-bad fixtures score lower than the good fixture."""
    good = make_good_spec()
    good_report = _eval_fn(good)
    good_score = good_report.composite_score

    fixtures = [
        ("good_spec", make_good_spec()),
        ("bad_missing_sections", make_bad_spec_missing_sections()),
        ("bad_vague_requirements", make_bad_spec_vague_requirements()),
        ("bad_no_traceability", make_bad_spec_no_traceability()),
        ("bad_contradictions", make_bad_spec_contradictions()),
        ("bad_no_uncertainty", make_bad_spec_no_uncertainty()),
    ]

    results = []
    for name, fixture in fixtures:
        report = _eval_fn(fixture)
        score = report.composite_score
        is_correct = (name == "good_spec" and score > 0.60) or (
            name != "good_spec" and score < good_score
        )
        results.append((name, is_correct, score))

    return results


def main() -> None:
    start = time.monotonic()
    print("=" * 60)
    print("RALPH LOOP — Meta-Evaluation")
    print("=" * 60)

    # Phase 1: Fixture validation
    print("\n--- FIXTURE VALIDATION ---")
    fixture_results = _run_fixture_validation()
    all_correct = True
    for name, correct, score in fixture_results:
        status = "CORRECT" if correct else "WRONG"
        print(f"  {name:30s} score={score:.3f}  {status}")
        if not correct:
            all_correct = False

    if not all_correct:
        print("\nWARNING: Some fixtures scored incorrectly — eval needs work")

    # Phase 2: Mutation testing
    print("\n--- MUTATION TESTING ---")
    good_input = make_good_spec()
    mutation_results = run_mutation_suite(good_input, _eval_fn)

    for r in mutation_results:
        status = "CAUGHT" if r.caught else "SURVIVED"
        print(
            f"  {r.mutation.name:25s} "
            f"baseline={r.baseline_score:.3f} "
            f"mutated={r.mutated_score:.3f} "
            f"drop={r.score_drop:+.3f} "
            f"expected_drop={r.mutation.expected_drop:.3f} "
            f"{status}"
        )

    kill_rate = mutation_kill_rate(mutation_results)
    survived = [r for r in mutation_results if r.survived]

    print(f"\nKILL_RATE: {kill_rate:.0%} ({len(mutation_results) - len(survived)}/{len(mutation_results)})")

    if survived:
        print("\n--- BLIND SPOTS (surviving mutations) ---")
        for r in survived:
            print(f"  SURVIVED: {r.mutation.name} — {r.mutation.description}")
            print(f"           Target: {r.mutation.target_dimension.value}")
            print(f"           Score drop: {r.score_drop:+.3f} (needed {r.mutation.expected_drop:+.3f})")

    elapsed = time.monotonic() - start
    print(f"\nElapsed: {elapsed:.1f}s")

    # Log to results file
    results_file = Path("ralph_results.tsv")
    if not results_file.exists():
        results_file.write_text("timestamp\tkill_rate\tmutations\tsurvived\tfixture_correct\telapsed_s\n")
    with results_file.open("a") as f:
        import datetime
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        f.write(f"{ts}\t{kill_rate:.3f}\t{len(mutation_results)}\t{len(survived)}\t{all_correct}\t{elapsed:.1f}\n")

    # Exit code: 0 if perfect, 1 if blind spots remain
    sys.exit(0 if kill_rate >= 1.0 and all_correct else 1)


if __name__ == "__main__":
    main()
