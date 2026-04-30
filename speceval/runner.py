"""Main evaluation runner — orchestrates Tier 1 + Tier 2 evaluation.

Inspired by Karpathy's autoresearch loop:
  1. Take input (source docs + template + goals + generated spec)
  2. Run deterministic checks (Tier 1) — seconds
  3. Run LLM-as-judge (Tier 2) — minutes
  4. Produce EvalReport with composite score
  5. Log to results.tsv for tracking across experiments
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from speceval.schema import (
    Dimension,
    DimensionScore,
    EvalInput,
    EvalReport,
)
from speceval.tier1.consistency import evaluate_consistency
from speceval.tier1.precision import evaluate_requirement_precision
from speceval.tier1.structural import StructuralConfig, evaluate_structural_completeness
from speceval.tier1.traceability import evaluate_traceability
from speceval.tier1.uncertainty import evaluate_uncertainty_transparency
from speceval.tier2.judge import JudgeConfig, run_tier2_eval


@dataclass
class RunConfig:
    """Configuration for a full evaluation run."""

    run_tier1: bool = True
    run_tier2: bool = False  # Off by default — requires LLM API keys
    tier1_config: StructuralConfig = field(default_factory=StructuralConfig)
    tier2_config: JudgeConfig = field(default_factory=JudgeConfig)
    results_file: Path | None = None


def run_tier1(eval_input: EvalInput, config: RunConfig) -> dict[Dimension, DimensionScore]:
    """Run all Tier 1 deterministic evaluators."""
    results: dict[Dimension, DimensionScore] = {}

    results[Dimension.STRUCTURAL_COMPLETENESS] = evaluate_structural_completeness(
        eval_input, config.tier1_config
    )
    results[Dimension.REQUIREMENT_PRECISION] = evaluate_requirement_precision(eval_input)
    results[Dimension.TRACEABILITY] = evaluate_traceability(eval_input)
    results[Dimension.CONSISTENCY] = evaluate_consistency(eval_input)
    results[Dimension.UNCERTAINTY_TRANSPARENCY] = evaluate_uncertainty_transparency(eval_input)

    return results


def run_full_eval(eval_input: EvalInput, config: RunConfig | None = None) -> EvalReport:
    """Run the complete evaluation pipeline."""
    config = config or RunConfig()
    start = time.monotonic()

    report = EvalReport(input_hash=eval_input.input_hash)

    # Tier 1: Deterministic (always runs)
    if config.run_tier1:
        tier1_results = run_tier1(eval_input, config)
        report.dimension_scores.update(tier1_results)
        for ds in tier1_results.values():
            report.diagnostics.extend(ds.diagnostics)

    # Tier 2: LLM-as-Judge (opt-in)
    if config.run_tier2:
        tier2_results = run_tier2_eval(eval_input, config.tier2_config)
        report.dimension_scores.update(tier2_results)
        for ds in tier2_results.values():
            report.diagnostics.extend(ds.diagnostics)

    elapsed = time.monotonic() - start
    report.metadata["elapsed_seconds"] = round(elapsed, 2)
    report.metadata["tier1_enabled"] = config.run_tier1
    report.metadata["tier2_enabled"] = config.run_tier2

    # Log results
    if config.results_file:
        _append_results(config.results_file, report)

    return report


def _append_results(path: Path, report: EvalReport) -> None:
    """Append eval results to a TSV file (autoresearch-style logging)."""
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        header = "input_hash\tcomposite\tpassed\ttotal\telapsed_s\tdiagnostics\n"
        path.write_text(header)

    line = (
        f"{report.input_hash}\t"
        f"{report.composite_score:.4f}\t"
        f"{report.passed_count}\t"
        f"{report.total_count}\t"
        f"{report.metadata.get('elapsed_seconds', 0)}\t"
        f"{len(report.diagnostics)}\n"
    )
    with path.open("a") as f:
        f.write(line)


def report_to_markdown(report: EvalReport) -> str:
    """Render an EvalReport as human-readable Markdown."""
    lines = [
        "# Spec Evaluation Report",
        "",
        f"**Composite Score:** {report.composite_score:.3f}",
        f"**Dimensions Passed:** {report.passed_count}/{report.total_count}",
        f"**Total Diagnostics:** {len(report.diagnostics)}",
        "",
        "## Dimension Scores",
        "",
        "| Dimension | Score | Threshold | Pass | Confidence |",
        "|---|---|---|---|---|",
    ]

    for dim in Dimension:
        if dim in report.dimension_scores:
            ds = report.dimension_scores[dim]
            status = "PASS" if ds.passed else "FAIL"
            lines.append(
                f"| {dim.value} | {ds.score:.3f} | {ds.pass_threshold:.2f} | {status} | {ds.confidence:.1f} |"
            )

    if report.diagnostics:
        lines.extend([
            "",
            "## Diagnostics",
            "",
            "| Severity | Dimension | Message |",
            "|---|---|---|",
        ])
        for d in sorted(report.diagnostics, key=lambda x: x.severity.value):
            lines.append(f"| {d.severity.value} | {d.dimension.value} | {d.message[:100]} |")

    if report.metadata:
        lines.extend([
            "",
            f"*Elapsed: {report.metadata.get('elapsed_seconds', '?')}s*",
        ])

    return "\n".join(lines)
