"""Tests for the core I/O schema."""

from speceval.schema import (
    DEFAULT_WEIGHTS,
    Dimension,
    DimensionScore,
    EvalInput,
    EvalReport,
    GeneratedSpec,
    SourceDocument,
)


def test_dimension_enum_has_8_values():
    assert len(Dimension) == 8


def test_default_weights_sum_to_one():
    total = sum(DEFAULT_WEIGHTS.values())
    assert abs(total - 1.0) < 0.001


def test_eval_input_hash_deterministic():
    inp = EvalInput(
        sources=[SourceDocument("a.py", "hello", "CODE")],
        generated_spec=GeneratedSpec(title="test", markdown="# Test"),
    )
    h1 = inp.input_hash
    h2 = inp.input_hash
    assert h1 == h2
    assert len(h1) == 16


def test_eval_report_composite_score():
    report = EvalReport(input_hash="abc123")
    report.dimension_scores[Dimension.STRUCTURAL_COMPLETENESS] = DimensionScore(
        dimension=Dimension.STRUCTURAL_COMPLETENESS, score=0.9
    )
    report.dimension_scores[Dimension.REQUIREMENT_PRECISION] = DimensionScore(
        dimension=Dimension.REQUIREMENT_PRECISION, score=0.8
    )
    score = report.composite_score
    assert 0.0 < score < 1.0


def test_eval_report_all_passed():
    report = EvalReport(input_hash="abc123")
    report.dimension_scores[Dimension.STRUCTURAL_COMPLETENESS] = DimensionScore(
        dimension=Dimension.STRUCTURAL_COMPLETENESS, score=0.99
    )
    assert report.all_passed  # Only one dimension, and it passes


def test_dimension_score_pass_thresholds():
    ds = DimensionScore(dimension=Dimension.STRUCTURAL_COMPLETENESS, score=0.96)
    assert ds.passed  # Threshold is 0.95

    ds_fail = DimensionScore(dimension=Dimension.STRUCTURAL_COMPLETENESS, score=0.90)
    assert not ds_fail.passed


def test_source_document_hash():
    doc = SourceDocument("test.py", "hello world")
    assert len(doc.content_hash) == 16
    # Same content → same hash
    doc2 = SourceDocument("other.py", "hello world")
    assert doc.content_hash == doc2.content_hash
