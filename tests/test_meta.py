"""Tests for meta-evaluation (mutation testing)."""

from speceval.fixtures.synthetic import make_good_spec
from speceval.meta.mutation import (
    MUTATIONS,
    MutationResult,
    mutation_kill_rate,
    run_mutation_suite,
)
from speceval.runner import RunConfig, run_full_eval
from speceval.schema import EvalInput, EvalReport


def _eval_fn(eval_input: EvalInput) -> EvalReport:
    config = RunConfig(run_tier1=True, run_tier2=False)
    return run_full_eval(eval_input, config)


class TestMutations:
    def test_all_mutations_produce_valid_input(self):
        good = make_good_spec()
        for mutation in MUTATIONS:
            mutated = mutation.apply(good)
            assert isinstance(mutated, EvalInput)
            assert mutated.generated_spec.markdown  # Non-empty

    def test_mutations_change_the_spec(self):
        good = make_good_spec()
        for mutation in MUTATIONS:
            mutated = mutation.apply(good)
            # At least the markdown or claims should differ
            assert (
                mutated.generated_spec.markdown != good.generated_spec.markdown
                or mutated.generated_spec.claims != good.generated_spec.claims
            ), f"Mutation {mutation.name} did not change the spec"


class TestMutationSuite:
    def test_suite_runs_without_error(self):
        results = run_mutation_suite(make_good_spec(), _eval_fn)
        assert len(results) == len(MUTATIONS)
        for r in results:
            assert isinstance(r, MutationResult)

    def test_kill_rate_is_valid(self):
        results = run_mutation_suite(make_good_spec(), _eval_fn)
        rate = mutation_kill_rate(results)
        assert 0.0 <= rate <= 1.0

    def test_baseline_scores_higher_than_mutated(self):
        """For most mutations, the baseline should score higher on the target dimension."""
        results = run_mutation_suite(make_good_spec(), _eval_fn)
        # At least some mutations should be caught
        caught = [r for r in results if r.caught]
        assert len(caught) > 0, "No mutations caught — eval is broken"


class TestKillRate:
    def test_empty_results(self):
        assert mutation_kill_rate([]) == 0.0

    def test_all_caught(self):
        results = [
            MutationResult(
                mutation=MUTATIONS[0],
                baseline_score=0.9,
                mutated_score=0.5,
                caught=True,
                score_drop=0.4,
            ),
        ]
        assert mutation_kill_rate(results) == 1.0

    def test_none_caught(self):
        results = [
            MutationResult(
                mutation=MUTATIONS[0],
                baseline_score=0.9,
                mutated_score=0.85,
                caught=False,
                score_drop=0.05,
            ),
        ]
        assert mutation_kill_rate(results) == 0.0
