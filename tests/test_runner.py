"""Tests for the main evaluation runner."""

from speceval.fixtures.synthetic import (
    make_bad_spec_missing_sections,
    make_bad_spec_vague_requirements,
    make_good_spec,
)
from speceval.runner import RunConfig, report_to_markdown, run_full_eval
from speceval.schema import Dimension


class TestRunner:
    def test_tier1_only(self):
        config = RunConfig(run_tier1=True, run_tier2=False)
        report = run_full_eval(make_good_spec(), config)
        assert report.composite_score > 0.0
        assert len(report.dimension_scores) >= 5  # 5 Tier 1 dimensions

    def test_tier1_and_tier2_mock(self):
        from speceval.tier2.judge import JudgeConfig, MockProvider
        config = RunConfig(
            run_tier1=True,
            run_tier2=True,
            tier2_config=JudgeConfig(providers=[MockProvider(default_score=4)]),
        )
        report = run_full_eval(make_good_spec(), config)
        assert len(report.dimension_scores) >= 5

    def test_good_spec_beats_bad_spec(self):
        config = RunConfig(run_tier1=True, run_tier2=False)
        good_report = run_full_eval(make_good_spec(), config)
        bad_report = run_full_eval(make_bad_spec_missing_sections(), config)
        assert good_report.composite_score > bad_report.composite_score

    def test_report_has_metadata(self):
        report = run_full_eval(make_good_spec())
        assert "elapsed_seconds" in report.metadata
        assert report.metadata["elapsed_seconds"] >= 0


class TestReportToMarkdown:
    def test_renders_without_error(self):
        report = run_full_eval(make_good_spec())
        md = report_to_markdown(report)
        assert "# Spec Evaluation Report" in md
        assert "Composite Score" in md

    def test_includes_dimension_table(self):
        report = run_full_eval(make_good_spec())
        md = report_to_markdown(report)
        assert "Dimension" in md
        assert "Score" in md

    def test_includes_diagnostics(self):
        report = run_full_eval(make_bad_spec_vague_requirements())
        md = report_to_markdown(report)
        assert "Diagnostics" in md
