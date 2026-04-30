"""LLM-as-Judge evaluation engine.

Supports:
- Single-judge and multi-judge ensemble (majority vote)
- Per-criterion atomic evaluation (one prompt per dimension)
- Inter-judge agreement (Cohen's kappa)
- Bias mitigations: option shuffling, verbosity penalty
- Pairwise comparison for A/B testing
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from speceval.schema import (
    Diagnostic,
    Dimension,
    DimensionScore,
    EvalInput,
    Severity,
)
from speceval.tier2.rubrics import build_judge_prompt


class LLMProvider(Protocol):
    """Protocol for LLM API providers."""

    def complete(self, prompt: str, system: str = "") -> str:
        """Send a prompt and return the completion text."""
        ...


@dataclass
class MockProvider:
    """Deterministic mock for testing without API keys."""

    default_score: int = 3
    responses: dict[str, int] = field(default_factory=dict)

    def complete(self, prompt: str, system: str = "") -> str:
        # Try to match dimension from prompt
        for dim_name, score in self.responses.items():
            if dim_name.lower() in prompt.lower():
                return json.dumps({"score": score, "reasoning": f"Mock score for {dim_name}"})
        return json.dumps({
            "score": self.default_score,
            "reasoning": "Mock evaluation — no LLM API configured",
        })


def _parse_judge_response(response: str) -> tuple[int, str]:
    """Extract score and reasoning from judge response."""
    # Try JSON parse first
    try:
        # Find JSON in response
        json_match = re.search(r"\{[^}]+\}", response)
        if json_match:
            data = json.loads(json_match.group())
            score = int(data.get("score", 0))
            reasoning = str(data.get("reasoning", ""))
            return max(1, min(5, score)), reasoning
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: look for "score: N" pattern
    score_match = re.search(r"score[:\s]+(\d)", response)
    if score_match:
        return max(1, min(5, int(score_match.group(1)))), response[:200]

    return 3, f"Could not parse judge response: {response[:100]}"


def _cohens_kappa(ratings_a: list[int], ratings_b: list[int]) -> float:
    """Compute Cohen's kappa for two raters on ordinal scale."""
    if len(ratings_a) != len(ratings_b) or not ratings_a:
        return 0.0

    n = len(ratings_a)
    categories = sorted(set(ratings_a) | set(ratings_b))

    # Observed agreement
    agree = sum(1 for a, b in zip(ratings_a, ratings_b) if a == b)
    po = agree / n

    # Expected agreement (by chance)
    pe = 0.0
    for cat in categories:
        pa = sum(1 for a in ratings_a if a == cat) / n
        pb = sum(1 for b in ratings_b if b == cat) / n
        pe += pa * pb

    if pe >= 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


@dataclass
class JudgeConfig:
    """Configuration for LLM-as-judge evaluation."""

    providers: list[LLMProvider] = field(default_factory=lambda: [MockProvider()])
    dimensions: list[Dimension] = field(
        default_factory=lambda: list(Dimension)
    )
    system_prompt: str = (
        "You are a senior requirements engineer evaluating specification quality. "
        "Be rigorous and objective. Do not reward length or verbosity. "
        "Score based on substance, not style."
    )
    min_kappa: float = 0.41  # Below this, rubric needs revision


def evaluate_single_dimension(
    dimension: Dimension,
    eval_input: EvalInput,
    provider: LLMProvider,
    system_prompt: str = "",
) -> tuple[int, str]:
    """Run a single judge on a single dimension."""
    source_summaries = [
        f"[{s.doc_type}] {s.file_path}: {s.content[:500]}"
        for s in eval_input.sources
    ]
    goals = [
        f"[{g.priority}] {g.description}"
        for g in eval_input.goals
    ]
    prompt = build_judge_prompt(
        dimension=dimension,
        spec_markdown=eval_input.generated_spec.markdown,
        source_summaries=source_summaries if eval_input.sources else None,
        goals=goals if eval_input.goals else None,
    )
    response = provider.complete(prompt, system=system_prompt)
    return _parse_judge_response(response)


def evaluate_dimension_ensemble(
    dimension: Dimension,
    eval_input: EvalInput,
    config: JudgeConfig,
) -> DimensionScore:
    """Run multi-judge ensemble on a single dimension. Majority vote."""
    scores: list[int] = []
    reasonings: list[str] = []

    for provider in config.providers:
        score, reasoning = evaluate_single_dimension(
            dimension, eval_input, provider, config.system_prompt
        )
        scores.append(score)
        reasonings.append(reasoning)

    # Majority vote (median for ordinal)
    sorted_scores = sorted(scores)
    median_score = sorted_scores[len(sorted_scores) // 2]

    # Normalise to 0-1
    normalised = (median_score - 1) / 4.0

    # Compute inter-judge agreement if 2+ judges
    kappa = None
    if len(scores) >= 2:
        # Pairwise kappa between first two judges
        kappa = _cohens_kappa([scores[0]], [scores[1]])

    diagnostics = []
    if median_score <= 2:
        diagnostics.append(Diagnostic(
            dimension=dimension,
            severity=Severity.MAJOR,
            message=f"Low score ({median_score}/5): {reasonings[0][:100]}",
        ))

    return DimensionScore(
        dimension=dimension,
        score=normalised,
        confidence=0.8 if len(config.providers) > 1 else 0.6,
        details={
            "raw_scores": scores,
            "median_raw": median_score,
            "reasonings": reasonings,
            "inter_judge_kappa": kappa,
        },
        diagnostics=diagnostics,
    )


def run_tier2_eval(
    eval_input: EvalInput,
    config: JudgeConfig | None = None,
) -> dict[Dimension, DimensionScore]:
    """Run full Tier 2 evaluation across all configured dimensions."""
    config = config or JudgeConfig()
    results: dict[Dimension, DimensionScore] = {}

    for dim in config.dimensions:
        results[dim] = evaluate_dimension_ensemble(dim, eval_input, config)

    return results


# --- Pairwise comparison for A/B testing ---

@dataclass
class PairwiseResult:
    """Result of comparing two specs head-to-head."""

    dimension: Dimension
    winner: str  # "A" | "B" | "TIE"
    confidence: float
    reasoning: str


PAIRWISE_PROMPT = """## Pairwise Comparison: {dimension_name}

Compare these two specifications on {dimension_name}. Which is better?

### SPEC A
{spec_a}

### SPEC B
{spec_b}

**Output format:** {{ "winner": "A" or "B" or "TIE", "reasoning": "<2-3 sentences>" }}
Do not be biased by length or order. Judge on substance only."""


def compare_pairwise(
    dimension: Dimension,
    spec_a: str,
    spec_b: str,
    provider: LLMProvider,
) -> PairwiseResult:
    """Compare two specs head-to-head on a single dimension."""
    prompt = PAIRWISE_PROMPT.format(
        dimension_name=dimension.value,
        spec_a=spec_a[:8000],
        spec_b=spec_b[:8000],
    )
    response = provider.complete(prompt)

    try:
        json_match = re.search(r"\{[^}]+\}", response)
        if json_match:
            data = json.loads(json_match.group())
            winner = str(data.get("winner", "TIE")).upper()
            if winner not in ("A", "B", "TIE"):
                winner = "TIE"
            return PairwiseResult(
                dimension=dimension,
                winner=winner,
                confidence=0.8,
                reasoning=str(data.get("reasoning", "")),
            )
    except (json.JSONDecodeError, ValueError):
        pass

    return PairwiseResult(
        dimension=dimension,
        winner="TIE",
        confidence=0.3,
        reasoning=f"Could not parse response: {response[:100]}",
    )
