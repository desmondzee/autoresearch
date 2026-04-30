"""Tests for Tier 2 LLM-as-judge evaluation (using mock provider)."""

import json

from speceval.fixtures.synthetic import make_good_spec
from speceval.schema import Dimension
from speceval.tier2.judge import (
    JudgeConfig,
    MockProvider,
    PairwiseResult,
    _cohens_kappa,
    _parse_judge_response,
    compare_pairwise,
    evaluate_dimension_ensemble,
    run_tier2_eval,
)


class TestParseJudgeResponse:
    def test_valid_json(self):
        response = '{"score": 4, "reasoning": "Good quality spec"}'
        score, reasoning = _parse_judge_response(response)
        assert score == 4
        assert "Good quality" in reasoning

    def test_json_in_text(self):
        response = 'After analysis, here is my evaluation: {"score": 3, "reasoning": "Average"}'
        score, reasoning = _parse_judge_response(response)
        assert score == 3

    def test_clamps_to_range(self):
        response = '{"score": 7, "reasoning": "test"}'
        score, _ = _parse_judge_response(response)
        assert score == 5

        response = '{"score": 0, "reasoning": "test"}'
        score, _ = _parse_judge_response(response)
        assert score == 1

    def test_fallback_pattern(self):
        response = "The score: 4 because it is well-structured"
        score, _ = _parse_judge_response(response)
        assert score == 4

    def test_unparseable_defaults_to_3(self):
        response = "I cannot evaluate this"
        score, _ = _parse_judge_response(response)
        assert score == 3


class TestCohensKappa:
    def test_perfect_agreement(self):
        kappa = _cohens_kappa([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
        assert kappa == 1.0

    def test_empty_input(self):
        assert _cohens_kappa([], []) == 0.0

    def test_partial_agreement(self):
        kappa = _cohens_kappa([1, 2, 3], [1, 2, 4])
        assert 0.0 < kappa < 1.0


class TestMockProvider:
    def test_default_score(self):
        provider = MockProvider(default_score=4)
        response = provider.complete("test prompt")
        data = json.loads(response)
        assert data["score"] == 4

    def test_dimension_specific_score(self):
        provider = MockProvider(responses={"structural": 5})
        response = provider.complete("Evaluate structural completeness")
        data = json.loads(response)
        assert data["score"] == 5


class TestEnsembleEvaluation:
    def test_single_judge(self):
        config = JudgeConfig(providers=[MockProvider(default_score=4)])
        result = evaluate_dimension_ensemble(
            Dimension.STRUCTURAL_COMPLETENESS,
            make_good_spec(),
            config,
        )
        assert result.score == 0.75  # (4-1)/4

    def test_multi_judge_majority(self):
        config = JudgeConfig(providers=[
            MockProvider(default_score=4),
            MockProvider(default_score=5),
            MockProvider(default_score=4),
        ])
        result = evaluate_dimension_ensemble(
            Dimension.STRUCTURAL_COMPLETENESS,
            make_good_spec(),
            config,
        )
        assert result.score == 0.75  # Median of [4,4,5] = 4 → (4-1)/4


class TestPairwiseComparison:
    def test_pairwise_returns_result(self):
        provider = MockProvider()
        result = compare_pairwise(
            Dimension.STRUCTURAL_COMPLETENESS,
            "# Spec A\nContent A",
            "# Spec B\nContent B",
            provider,
        )
        assert isinstance(result, PairwiseResult)
        assert result.winner in ("A", "B", "TIE")


class TestFullTier2:
    def test_run_all_dimensions(self):
        config = JudgeConfig(
            providers=[MockProvider(default_score=4)],
            dimensions=[Dimension.STRUCTURAL_COMPLETENESS, Dimension.REQUIREMENT_PRECISION],
        )
        results = run_tier2_eval(make_good_spec(), config)
        assert len(results) == 2
        assert Dimension.STRUCTURAL_COMPLETENESS in results
        assert Dimension.REQUIREMENT_PRECISION in results
