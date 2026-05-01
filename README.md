# speceval — SOTA Benchmark for Agentic Specification Generation

Architecture-agnostic evaluation framework for benchmarking agentic specification generation pipelines. Built via iterative RALPH loops (Research → Assess → Learn → Plan → Harden), inspired by [Karpathy's autoresearch](https://github.com/karpathy/autoresearch).

## What it does

Takes the **inputs** (source documents, templates, goals) and **output** (generated spec) of any agentic spec generation pipeline and evaluates quality across **8 orthogonal dimensions**:

| Dimension | What it measures | Eval tier |
|---|---|---|
| D1 Structural Completeness | Required sections present, non-empty | Tier 1 (deterministic) |
| D2 Requirement Precision | RFC 2119, EARS compliance, no vague terms | Tier 1 |
| D3 Legacy Fidelity | Faithful to source material | Tier 2 (LLM-as-judge) |
| D4 Gap Coverage | Gaps identified and categorised | Tier 2 |
| D5 Traceability | Citations valid, goals linked | Tier 1 |
| D6 Consistency | No contradictions, terminology consistent | Tier 1 |
| D7 Decision Readiness | Actionable for non-technical decision-makers | Tier 2 |
| D8 Uncertainty Transparency | TBD/assumptions flagged honestly | Tier 1 |

## Quick start

```bash
# Install
uv sync --all-extras

# Run tests (51 tests)
uv run pytest tests/ -v

# Run the RALPH meta-eval (mutation testing)
uv run python -m speceval.meta.run_ralph
```

## Architecture

```
speceval/
├── schema.py          # I/O contract: EvalInput → EvalReport
├── runner.py          # Orchestrates Tier 1 + Tier 2
├── tier1/             # Deterministic evaluators (seconds, CI-gate)
│   ├── structural.py  # D1: Section presence, heading density
│   ├── precision.py   # D2: RFC 2119, EARS, vague terms, passive voice
│   ├── traceability.py # D5: Citation density/validity, goal coverage
│   ├── consistency.py  # D6: Keyword conflicts, duplicates, terminology
│   └── uncertainty.py  # D8: TBD markers, hedging detection
├── tier2/             # LLM-as-judge evaluators (minutes, PR-gate)
│   ├── rubrics.py     # Per-dimension scoring rubrics
│   └── judge.py       # Multi-judge ensemble, pairwise comparison
├── fixtures/          # Synthetic test fixtures
│   └── synthetic.py   # Good spec + 5 known-bad specs
└── meta/              # Meta-evaluation (does the eval itself work?)
    ├── mutation.py     # 10 mutation operators
    └── run_ralph.py    # RALPH loop runner
```

## RALPH Loop Results

Three iterations achieved **100% mutation kill rate** across 10 diverse mutations:

| Loop | Kill Rate | Mutations | Blind Spots Fixed |
|---|---|---|---|
| 1 | 60% (3/5) | 5 | - |
| 2 | 80% (4/5) | 5 | Structural: quadratic penalty + critical sections |
| 3 | 100% (10/10) | 10 | Consistency: cross-req semantic contradiction detector |

## Using with your pipeline

```python
from speceval.schema import EvalInput, SourceDocument, GeneratedSpec
from speceval.runner import run_full_eval, report_to_markdown

eval_input = EvalInput(
    sources=[SourceDocument("legacy.java", code, "CODE", "PAST")],
    generated_spec=GeneratedSpec(title="My Spec", markdown=spec_md),
)
report = run_full_eval(eval_input)
print(report_to_markdown(report))
```

## Research report

See [prd-modernization-benchmark-report.md](prd-modernization-benchmark-report.md) for the full research backing (30+ citations, survey of 5 evaluation method categories, three-tier architecture proposal).
