# speceval — autoresearch loop

This is an experiment to have an LLM iteratively improve a specification
evaluation benchmark. Inspired by [Karpathy's autoresearch](https://github.com/karpathy/autoresearch).

## The RALPH Loop

RALPH = **R**esearch → **A**ssess → **L**earn → **P**lan → **H**arden

Each iteration:
1. **Research** — Read the current eval code, understand what it measures
2. **Assess** — Run the meta-eval (mutation suite) to find blind spots
3. **Learn** — Analyse which mutations survived and why
4. **Plan** — Design fixes for the blind spots
5. **Harden** — Implement the fixes, re-run meta-eval, verify improvement

## Setup

1. Install dependencies: `uv sync`
2. Run the baseline: `uv run pytest tests/ -v`
3. Run the meta-eval: `uv run python -m speceval.meta.run_ralph`

## The experiment loop

LOOP FOREVER:

1. Run the meta-eval: `uv run python -m speceval.meta.run_ralph > ralph.log 2>&1`
2. Read the results: `grep "KILL_RATE\|SURVIVED\|CAUGHT" ralph.log`
3. If kill rate < 1.0, there are blind spots to fix:
   - Read the SURVIVED mutations to understand what the eval missed
   - Modify the eval code (speceval/tier1/*.py or speceval/tier2/*.py)
   - Add new mutations if you discover new defect categories
4. Re-run the meta-eval to verify improvement
5. Log results to results.tsv
6. Commit changes

**Target:** 100% mutation kill rate with ≥10 diverse mutations.

**What you CAN modify:**
- `speceval/tier1/*.py` — deterministic evaluators
- `speceval/tier2/*.py` — LLM-as-judge evaluators
- `speceval/meta/mutation.py` — add new mutations
- `speceval/fixtures/synthetic.py` — add new test fixtures
- `tests/*.py` — add new tests

**What you CANNOT modify:**
- `speceval/schema.py` — the I/O contract is frozen
- Mutation definitions that already pass — don't weaken the eval

**NEVER STOP**: Once the loop begins, keep improving the eval until
manually stopped. If you can't improve the kill rate, add harder
mutations, add new defect categories, or refine existing detectors.
