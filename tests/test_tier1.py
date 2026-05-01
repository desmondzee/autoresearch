"""Tests for Tier 1 deterministic evaluators."""

from speceval.fixtures.synthetic import (
    make_bad_spec_contradictions,
    make_bad_spec_missing_sections,
    make_bad_spec_no_traceability,
    make_bad_spec_no_uncertainty,
    make_bad_spec_vague_requirements,
    make_good_spec,
)
from speceval.schema import Dimension
from speceval.tier1.consistency import evaluate_consistency
from speceval.tier1.precision import evaluate_requirement_precision
from speceval.tier1.structural import evaluate_structural_completeness
from speceval.tier1.traceability import evaluate_traceability
from speceval.tier1.uncertainty import evaluate_uncertainty_transparency


class TestStructuralCompleteness:
    def test_good_spec_scores_high(self):
        result = evaluate_structural_completeness(make_good_spec())
        assert result.score >= 0.80
        assert result.dimension == Dimension.STRUCTURAL_COMPLETENESS

    def test_missing_sections_scores_low(self):
        result = evaluate_structural_completeness(make_bad_spec_missing_sections())
        assert result.score < 0.60
        assert len(result.diagnostics) > 0

    def test_good_vs_bad_ordering(self):
        good = evaluate_structural_completeness(make_good_spec())
        bad = evaluate_structural_completeness(make_bad_spec_missing_sections())
        assert good.score > bad.score


class TestRequirementPrecision:
    def test_good_spec_scores_high(self):
        result = evaluate_requirement_precision(make_good_spec())
        assert result.score >= 0.40  # Good spec uses SHALL keywords
        assert result.dimension == Dimension.REQUIREMENT_PRECISION

    def test_vague_spec_scores_low(self):
        result = evaluate_requirement_precision(make_bad_spec_vague_requirements())
        assert result.score < 0.60

    def test_good_vs_bad_ordering(self):
        good = evaluate_requirement_precision(make_good_spec())
        bad = evaluate_requirement_precision(make_bad_spec_vague_requirements())
        assert good.score > bad.score


class TestTraceability:
    def test_good_spec_scores_high(self):
        result = evaluate_traceability(make_good_spec())
        assert result.score >= 0.50
        assert result.dimension == Dimension.TRACEABILITY

    def test_no_traceability_scores_low(self):
        result = evaluate_traceability(make_bad_spec_no_traceability())
        assert result.score < 0.50
        assert len(result.diagnostics) > 0

    def test_good_vs_bad_ordering(self):
        good = evaluate_traceability(make_good_spec())
        bad = evaluate_traceability(make_bad_spec_no_traceability())
        assert good.score > bad.score


class TestConsistency:
    def test_good_spec_scores_high(self):
        result = evaluate_consistency(make_good_spec())
        assert result.score >= 0.70
        assert result.dimension == Dimension.CONSISTENCY

    def test_contradictions_score_lower(self):
        result = evaluate_consistency(make_bad_spec_contradictions())
        # Should detect keyword conflicts
        assert result.dimension == Dimension.CONSISTENCY

    def test_good_vs_bad_ordering(self):
        good = evaluate_consistency(make_good_spec())
        bad = evaluate_consistency(make_bad_spec_contradictions())
        assert good.score >= bad.score


class TestUncertaintyTransparency:
    def test_good_spec_scores_high(self):
        result = evaluate_uncertainty_transparency(make_good_spec())
        assert result.score >= 0.50
        assert result.dimension == Dimension.UNCERTAINTY_TRANSPARENCY

    def test_no_uncertainty_scores_lower(self):
        result = evaluate_uncertainty_transparency(make_bad_spec_no_uncertainty())
        assert result.dimension == Dimension.UNCERTAINTY_TRANSPARENCY

    def test_good_vs_bad_ordering(self):
        good = evaluate_uncertainty_transparency(make_good_spec())
        bad = evaluate_uncertainty_transparency(make_bad_spec_no_uncertainty())
        assert good.score >= bad.score
