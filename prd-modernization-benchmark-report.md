# Benchmarking Agentic PRD Specification Modernisation

> **Purpose** — Evaluate methods for benchmarking a system that takes legacy documentation (policy documents, SOPs, existing specs) and produces modernised PRD-quality specifications through an agentic pipeline.
>
> **Scope** — Applicable to the ifactorial pipeline stages: Ingest → Align → Question → Generate.

---

## Table of Contents

1. [What Makes a Good Modernisation Spec](#1-what-makes-a-good-modernisation-spec)
2. [Quality Dimensions for PRD Specifications](#2-quality-dimensions-for-prd-specifications)
3. [Benchmark Method Survey](#3-benchmark-method-survey)
4. [Recommended Benchmark Architecture](#4-recommended-benchmark-architecture)
5. [Metric Catalogue](#5-metric-catalogue)
6. [Evaluation Rubric Design](#6-evaluation-rubric-design)
7. [Dataset & Ground-Truth Strategy](#7-dataset--ground-truth-strategy)
8. [Implementation Roadmap](#8-implementation-roadmap)
9. [References](#9-references)

---

## 1. What Makes a Good Modernisation Spec

A modernisation specification is not a green-field PRD. It inherits legacy constraints, must preserve institutional knowledge, and must surface gaps between current-state and target-state. The goals differ from typical product requirements.

### 1.1 Goals of Specifications (General)

Per IEEE 830 (superseded by ISO/IEC/IEEE 29148:2011), a good SRS must be:

| Property | Definition |
|---|---|
| **Correct** | Every stated requirement reflects a real need |
| **Unambiguous** | Every requirement has exactly one interpretation |
| **Complete** | All significant requirements and responses are documented |
| **Consistent** | No internal contradictions between requirements |
| **Ranked for importance** | Essential vs. conditional vs. optional |
| **Verifiable** | Each requirement can be checked by a finite, cost-effective process |
| **Modifiable** | Structure permits changes without cascading rewrites |
| **Traceable** | Origin of each requirement is clear; forward-traceable to design |

*Source: IEEE 830-1998 §4.3; ISO/IEC/IEEE 29148:2011*

### 1.2 Additional Goals for Modernisation Specs

Beyond standard IEEE qualities, a modernisation PRD has domain-specific requirements:

| Goal | Why It Matters |
|---|---|
| **Legacy-fidelity** | The spec must faithfully capture what the existing system does before proposing what it should do |
| **Gap visibility** | Missing requirements, lost knowledge, and contradictions between legacy and target must be surfaced explicitly |
| **Evidence & citation** | Every claim should be traceable back to a source document, interview, or code artefact |
| **Decision-readiness** | The spec should be structured for non-technical decision-makers: choose → edit → sign |
| **Uncertainty surfacing** | Where information is missing or ambiguous, the spec must flag it rather than hallucinate |
| **Regulatory alignment** | Government/enterprise modernisation specs must map to compliance frameworks |
| **Iterative refinement** | Each signed decision should feed back, re-aligning the spec until baselined |

### 1.3 What Specifically Makes a PRD "Good" for System Modernisation

Research from productic.net, Jama Software, and the SpecOps methodology converges on these properties:

1. **Problem-first framing** — "Why" before "What". The spec answers what problem exists in the legacy system before prescribing solutions.
2. **Testable acceptance criteria** — Every requirement is verifiable: "The system SHALL process batch imports of ≥10,000 records within 5 minutes" vs. "The system should be fast."
3. **Stakeholder-scoped** — Different sections address different audiences (policy-makers, engineers, operators).
4. **Evidence-backed** — Claims cite source material. The 2022 Birmingham City Council ERP failure (£100M loss) is a canonical example of what happens when requirements are under-specified.
5. **Gap-aware** — Explicitly surfaces what the legacy system does that isn't planned for the target, what's new, and what behaves differently.

---

## 2. Quality Dimensions for PRD Specifications

Based on the research, we propose **eight orthogonal quality dimensions** for evaluating generated modernisation specs. These synthesise IEEE 29148, CRACQ (Coherence/Rigor/Appropriateness/Completeness/Quality), and domain-specific modernisation needs.

| # | Dimension | What It Measures | Signal Type |
|---|---|---|---|
| D1 | **Structural Completeness** | Are all required sections present? (purpose, scope, stakeholders, requirements, acceptance criteria, constraints, dependencies, glossary) | Deterministic |
| D2 | **Requirement Precision** | Are requirements unambiguous, testable, and well-formed? (EARS syntax, SHALL/SHOULD/MAY usage) | NLP + LLM |
| D3 | **Legacy Fidelity** | Does the spec accurately capture what the existing system does? | Reference-based |
| D4 | **Gap Coverage** | Are gaps between current-state and target-state explicitly identified and categorised? | LLM-as-judge |
| D5 | **Traceability** | Can every requirement be traced to a source (document, interview, code)? Are citations valid? | Deterministic |
| D6 | **Consistency** | Are there contradictions within the spec or between the spec and source material? | NLP + LLM |
| D7 | **Decision Readiness** | Is the spec structured for non-technical review? Are options presented with evidence? | LLM-as-judge |
| D8 | **Uncertainty Transparency** | Does the spec explicitly flag unknowns, assumptions, and areas needing human input? | Pattern-match + LLM |

---

## 3. Benchmark Method Survey

### 3.1 Reference-Based Evaluation

**Approach**: Compare generated spec against a gold-standard human-authored spec.

| Method | How It Works | Strengths | Weaknesses |
|---|---|---|---|
| **BLEU/ROUGE** | N-gram overlap between generated and reference text | Fast, deterministic, well-understood | Weak correlation with human judgment for long documents; penalises valid paraphrasing |
| **BERTScore** | Contextual embedding similarity per token | Captures semantic equivalence beyond lexical match | Computationally heavier; still a single score |
| **SBC Score** | Reverse-generation technique: reconstruct requirements from output, compare to original (Ponnusamy 2025) | Detects hallucinations and missing features; combines BLEU + semantic similarity + completeness | Requires LLM for reverse generation; novel, less validated |
| **R2ABench Structural Metrics** | Graph-based comparison of entities + relationships in generated vs. reference architecture (Li et al. 2026) | Good for structural/architectural aspects; captures relational reasoning | Designed for architecture diagrams, not prose specs |

**Verdict**: Reference-based methods are useful for the **Legacy Fidelity (D3)** dimension but insufficient alone. They require gold-standard references, which are expensive to create, and don't capture modernisation-specific qualities like gap coverage or uncertainty transparency.

### 3.2 LLM-as-Judge Evaluation

**Approach**: Use a capable LLM (e.g. GPT-4, Claude) to score generated specs against a rubric.

| Method | How It Works | Strengths | Weaknesses |
|---|---|---|---|
| **Single-judge scoring** | One LLM scores on a rubric (e.g. 1-5 per dimension) | Simple, scalable, good for rapid iteration | Non-deterministic, position/verbosity bias |
| **Multi-judge ensemble** (Autorubric) | Multiple LLM judges score independently; aggregate via majority/weighted vote (Rao & Callison-Burch 2026) | Reduces individual judge bias; calibratable with few-shot examples | Higher cost; diminishing returns beyond 3 judges |
| **Per-criterion atomic evaluation** | Evaluate one dimension at a time with dimension-specific prompts | Prevents criterion conflation; more reliable per-dimension scores | More API calls; must design good criterion prompts |
| **CRACQ framework** | Multi-dimensional trait scoring: Coherence, Rigor, Appropriateness, Completeness, Quality (Soltani et al. 2025) | Trait-level diagnostics; more stable than direct LLM eval | Trained on grant proposals, may need domain adaptation |

**Verdict**: LLM-as-judge is the **strongest candidate for dimensions D4, D6, D7, D8** where there is no single correct answer. Key mitigations: use per-criterion atomic evaluation, few-shot calibration, and option shuffling for ordinal scales.

**Key insight from Autorubric**: Reliability metrics from psychometrics (Cohen's κ, weighted κ) should be used to validate judge consistency. If inter-judge κ < 0.41, the rubric needs revision, not more judges.

### 3.3 Deterministic / Heuristic Evaluation

**Approach**: Rule-based checks that don't require LLMs or references.

| Method | What It Checks | Applicable Dimensions |
|---|---|---|
| **Section presence checker** | Does the spec contain required sections? (regex/heading detection) | D1 (Structural Completeness) |
| **EARS pattern matcher** | Do requirements follow EARS syntax? (Easy Approach to Requirements Syntax) | D2 (Precision) |
| **SHALL/SHOULD/MAY counter** | RFC 2119 keyword usage consistency | D2 (Precision) |
| **Citation validator** | Are cited sources real and accessible? Do citation IDs resolve? | D5 (Traceability) |
| **Ambiguity detector** (QuARS) | NLP-based detection of vague terms, passive voice, dangling modifiers | D2, D6 |
| **Contradiction detector** | Negation/entailment analysis between requirement pairs | D6 (Consistency) |
| **Uncertainty keyword scanner** | Presence of explicit uncertainty markers: "TBD", "assumption", "to be confirmed" | D8 (Uncertainty Transparency) |

**Verdict**: Cheap, fast, reproducible. Should form the **foundation layer** of any benchmark. But they cannot assess semantic quality, gap reasoning, or decision-readiness.

### 3.4 Pairwise / Tournament Evaluation

**Approach**: Compare two generated specs head-to-head rather than scoring absolute quality.

| Method | How It Works | Strengths | Weaknesses |
|---|---|---|---|
| **ELO/Bradley-Terry ranking** | LLM or human judges pick the better spec from a pair; aggregate into rankings | More reliable than absolute scoring; reduces calibration issues | O(n²) comparisons; no absolute quality signal |
| **Varco Arena** (Son et al. 2024) | Single-elimination tournament with LLM judges; reference-free | Fast convergence to ranking; flexible benchmark updates | Ranking ≠ quality measurement; can't set pass/fail thresholds |

**Verdict**: Excellent for **comparing pipeline versions** (A/B testing prompt changes, model swaps, pipeline architecture changes). Not suitable as a standalone quality gate. Best used alongside rubric-based evaluation.

### 3.5 Execution-Based / Downstream Evaluation

**Approach**: Evaluate the spec by measuring what downstream consumers can do with it.

| Method | How It Works | Strengths | Weaknesses |
|---|---|---|---|
| **Spec → Code generation** | Feed the generated spec to a code-generation agent; measure code quality/test pass rate | Direct measure of spec actionability | Confounds spec quality with code-gen capability |
| **Spec → Architecture** (R2ABench) | Generate architecture diagrams from specs; compare against references | Measures structural information content | Narrow signal; doesn't test prose quality |
| **Human task completion** | Give humans the spec; measure time-to-understanding, decision accuracy, error rate | Gold standard for decision-readiness | Expensive, slow, not scalable for CI |
| **Round-trip fidelity** | Spec → Code → Reverse-engineer spec → Compare with original (SBC Score approach) | Detects hallucinations and completeness gaps | Two-hop LLM chain adds noise |

**Verdict**: Valuable for **D7 (Decision Readiness)** and as an end-to-end validation. Best reserved for periodic deep evaluation, not CI gating.

---

## 4. Recommended Benchmark Architecture

Based on the survey, we recommend a **three-tier evaluation architecture** that balances speed, cost, and depth.

```
┌──────────────────────────────────────────────────────────┐
│                   TIER 3: DEEP EVAL                      │
│  Human review panel + downstream task completion         │
│  Frequency: Monthly / milestone releases                 │
│  Cost: $$$   Speed: Days                                 │
├──────────────────────────────────────────────────────────┤
│                   TIER 2: LLM-AS-JUDGE                   │
│  Per-dimension rubric scoring (8 dimensions)             │
│  Multi-judge ensemble (3 judges, majority vote)          │
│  Pairwise comparison for version A/B testing             │
│  Frequency: Every pipeline change / PR                   │
│  Cost: $$    Speed: Minutes                              │
├──────────────────────────────────────────────────────────┤
│                   TIER 1: DETERMINISTIC                   │
│  Section presence · EARS syntax · Citation validity      │
│  Ambiguity detection · Contradiction check               │
│  Uncertainty keyword scan · SHALL/SHOULD/MAY count       │
│  Frequency: Every pipeline run (CI)                      │
│  Cost: $     Speed: Seconds                              │
└──────────────────────────────────────────────────────────┘
```

### 4.1 Per-Stage Evaluation

The ifactorial pipeline has four stages. Each stage has different output types and should be evaluated differently:

| Stage | Output | Primary Eval Tier | Key Dimensions |
|---|---|---|---|
| **Stage 1: Ingest** | Cited claims from source files | Tier 1 (deterministic) | D3 Legacy Fidelity, D5 Traceability |
| **Stage 2: Align** | Gap/classification report against goals + template | Tier 1 + Tier 2 | D4 Gap Coverage, D6 Consistency |
| **Stage 3: Question** | Recommended resolutions/questions from evidence | Tier 2 (LLM-as-judge) | D7 Decision Readiness, D8 Uncertainty |
| **Stage 4: Generate** | Final modernised specification | All tiers | All dimensions |

### 4.2 Composite Scoring

Each dimension D1–D8 produces a normalised score ∈ [0, 1]. The composite benchmark score is a weighted sum:

```
SCORE = Σ (wᵢ × Dᵢ)  where Σwᵢ = 1
```

**Suggested initial weights** (tunable via human calibration):

| Dimension | Weight | Rationale |
|---|---|---|
| D1 Structural Completeness | 0.10 | Table stakes — binary pass/fail |
| D2 Requirement Precision | 0.15 | Core spec quality |
| D3 Legacy Fidelity | 0.20 | Critical for modernisation trust |
| D4 Gap Coverage | 0.15 | Differentiator vs. generic PRDs |
| D5 Traceability | 0.15 | Auditability requirement |
| D6 Consistency | 0.10 | Standard quality gate |
| D7 Decision Readiness | 0.10 | UX of the spec |
| D8 Uncertainty Transparency | 0.05 | Safety net for hallucination |

---

## 5. Metric Catalogue

### 5.1 Tier 1 Metrics (Deterministic)

| Metric | Formula | Target |
|---|---|---|
| `section_coverage` | `|sections_present| / |sections_required|` | ≥ 0.95 |
| `ears_compliance` | `|EARS-formatted reqs| / |total reqs|` | ≥ 0.80 |
| `rfc2119_usage` | `|reqs with SHALL/SHOULD/MAY| / |total reqs|` | ≥ 0.90 |
| `citation_density` | `|cited claims| / |total claims|` | ≥ 0.85 |
| `citation_validity` | `|valid citations| / |total citations|` | ≥ 0.95 |
| `ambiguity_rate` | `|flagged vague terms| / |total terms|` | ≤ 0.05 |
| `uncertainty_flags` | `|explicit TBD/assumption markers| / |uncertainty_needing_sections|` | ≥ 0.80 |
| `passive_voice_rate` | `|passive constructions| / |total sentences|` | ≤ 0.20 |

### 5.2 Tier 2 Metrics (LLM-as-Judge)

Each dimension scored 1-5 by 3 judges. Report:
- **Median score** per dimension
- **Inter-judge agreement** (Cohen's κ; target ≥ 0.61 "substantial agreement")
- **Pairwise win rate** for A/B comparisons

| Metric | Method | Target |
|---|---|---|
| `legacy_fidelity_score` | Judge rates: "Does the spec accurately represent the current system?" | ≥ 4.0/5 |
| `gap_coverage_score` | Judge rates: "Are gaps between legacy and target identified and categorised?" | ≥ 4.0/5 |
| `consistency_score` | Judge rates: "Are there internal contradictions?" (inverse) | ≥ 4.0/5 |
| `decision_readiness_score` | Judge rates: "Could a non-technical decision-maker act on this?" | ≥ 3.5/5 |
| `uncertainty_score` | Judge rates: "Does the spec honestly flag what it doesn't know?" | ≥ 3.5/5 |

### 5.3 Tier 3 Metrics (Human / Downstream)

| Metric | Method | Target |
|---|---|---|
| `human_comprehension_time` | Time for domain expert to reach first decision on spec | Decreasing trend |
| `decision_accuracy` | Do human decisions based on spec match gold-standard expert decisions? | ≥ 0.85 |
| `spec_to_code_pass_rate` | Feed spec to code-gen agent; run generated tests | ≥ 0.70 |
| `round_trip_fidelity` | Spec → Code → Reverse-spec; compare reverse-spec to original | ≥ 0.75 BERTScore |

---

## 6. Evaluation Rubric Design

### 6.1 Rubric Structure (for Tier 2 LLM-as-Judge)

Each dimension gets its own evaluation prompt to avoid criterion conflation (per Autorubric guidance). Example rubric for **D4: Gap Coverage**:

```markdown
## Evaluation: Gap Coverage

You are evaluating a modernisation specification for gap coverage quality.

**Context**: You will receive:
1. The SOURCE DOCUMENTS (legacy system docs, policy docs)
2. The TARGET GOALS (modernisation objectives)
3. The GENERATED SPECIFICATION

**Score 1-5**:
- 5: Every gap between legacy and target is identified, categorised
     (missing/new/changed), and supported by evidence from source docs.
- 4: Most gaps identified and categorised; minor omissions in evidence.
- 3: Key gaps identified but categorisation is incomplete or evidence
     is sparse.
- 2: Some gaps mentioned but many are missed; no systematic coverage.
- 1: No meaningful gap analysis; spec reads as a generic PRD.

**Output format**:
{ "score": <1-5>, "reasoning": "<2-3 sentences>" }
```

### 6.2 Bias Mitigations

Drawing from Autorubric (Rao & Callison-Burch 2026) and Langfuse best practices:

| Bias | Mitigation |
|---|---|
| **Position bias** | Shuffle option order in ordinal rubrics |
| **Verbosity bias** | Include length penalty; "Do not reward length alone" in rubric |
| **Self-enhancement bias** | Use different model families as judges vs. generators |
| **Criterion conflation** | One prompt per dimension; never score multiple dimensions together |
| **Anchoring** | Randomise order of specs when doing pairwise comparison |

### 6.3 Calibration Protocol

1. **Create 10 calibration examples** spanning scores 1-5 for each dimension.
2. **Few-shot prime** each judge with 3 examples (one low, one mid, one high) before evaluation.
3. **Measure inter-judge κ** on the calibration set before proceeding.
4. If κ < 0.41, revise the rubric — the scoring criteria are ambiguous, not the judges.
5. **Re-calibrate monthly** as the pipeline evolves.

---

## 7. Dataset & Ground-Truth Strategy

### 7.1 Building a Gold-Standard Corpus

No existing benchmark covers modernisation PRD generation. We need to build one.

**Proposed approach**:

| Step | Action | Effort |
|---|---|---|
| 1 | **Collect 10-20 legacy document sets** from real or synthetic government/enterprise modernisation projects. Each set includes: policy docs, SOPs, existing specs, interview transcripts. | Medium |
| 2 | **Commission expert PRDs** — Have 2-3 domain experts independently write modernised PRDs for each legacy set. Measure inter-annotator agreement (κ). | High |
| 3 | **Annotate ground-truth gaps** — For each legacy→target pair, experts annotate all gaps, classify them (missing/new/changed), and link to source evidence. | High |
| 4 | **Create synthetic adversarial examples** — Inject known defects into good specs (remove citations, add contradictions, hide gaps) to test detector sensitivity. | Low |
| 5 | **Version and publish** — Use a structured format (JSON + Markdown) with schema validation. Iterate as the pipeline evolves. | Low |

### 7.2 Bootstrapping with Synthetic Data

For rapid iteration before gold-standard data is available:

1. **Use existing open-source specs** (e.g., SpecOps methodology repos, government RFPs) as source material.
2. **Generate "good" and "bad" specs** using the pipeline at different quality levels (e.g., with/without citation pass, with/without gap analysis).
3. **Validate synthetic labels** with a small expert panel (3-5 specs fully reviewed).

### 7.3 Continuous Benchmark Evolution

Inspired by SWE-bench's approach:
- New test cases are added from real pipeline runs where human reviewers flagged issues.
- Regression tests: specs that previously passed but were later found deficient become adversarial test cases.
- Version the benchmark alongside the pipeline.

---

## 8. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-3)

- [ ] Implement Tier 1 deterministic checks as a Python module
  - Section presence checker (parse Markdown headings)
  - Citation density and validity checker
  - Ambiguity detector (vague term list + passive voice NLP)
  - EARS pattern matcher (regex)
  - Uncertainty keyword scanner
- [ ] Create 5 synthetic legacy→spec test cases
- [ ] Set up CI to run Tier 1 on every pipeline output

### Phase 2: LLM-as-Judge (Weeks 3-5)

- [ ] Design rubric prompts for all 8 dimensions (see §6.1)
- [ ] Implement multi-judge evaluation harness
  - Support 3 judge models (e.g., GPT-4, Claude, Gemini)
  - Per-criterion atomic evaluation
  - Inter-judge κ computation
- [ ] Calibrate with 10 examples per dimension
- [ ] Implement pairwise comparison mode for A/B testing

### Phase 3: Ground Truth (Weeks 5-8)

- [ ] Commission 10 expert-authored modernisation PRDs
- [ ] Annotate gap ground truth
- [ ] Validate Tier 2 scores against expert rankings (correlation analysis)
- [ ] Tune dimension weights based on expert feedback

### Phase 4: Integration & Continuous Eval (Weeks 8-10)

- [ ] Integrate benchmark into pipeline CI/CD
- [ ] Dashboard for tracking quality trends across pipeline versions
- [ ] Automated regression detection (alert if any dimension drops >0.5)
- [ ] Monthly deep eval (Tier 3) cadence established

---

## 9. References

### Standards & Foundational Work
- IEEE 830-1998. *IEEE Recommended Practice for Software Requirements Specifications*. Superseded by ISO/IEC/IEEE 29148:2011.
- ISO/IEC/IEEE 29148:2011. *Systems and software engineering — Life cycle processes — Requirements engineering*.
- Stephen, E. & Mit, E. (2020). "Evaluation of Software Requirement Specification Based on IEEE 830 Quality Properties." *IJASEIT*, 10(4), 1396-1402.

### Benchmarks for Spec/Code Generation
- Chen, Z. et al. (2026). "CodeSpecBench: Benchmarking LLMs for Executable Behavioral Specification Generation." *arXiv:2604.12268*.
- Li, S. et al. (2026). "OSVBench: Benchmarking LLMs on Specification Generation Tasks for Operating System Verification." *AAAI-26*.
- Zhang, Z. et al. (2026). "SWE-AGI: Benchmarking Specification-Driven Software Construction with MoonBit." *arXiv:2602.09447*.
- Li, M. et al. (2026). "R2ABench: Benchmarking Requirement-to-Architecture Generation with Hybrid Evaluation." *arXiv:2604.06683*.
- Meaden, J. et al. (2026). "COMPASS: A Multi-Dimensional Benchmark for Evaluating Code Generation in Large Language Models." *arXiv:2508.13757*.

### Evaluation Frameworks
- Soltani, I. et al. (2025). "CRACQ: A Multi-Dimensional Approach to Automated Document Assessment." *arXiv:2510.02337*.
- Rao, D. & Callison-Burch, C. (2026). "Autorubric: A Unified Framework for Rubric-Based LLM Evaluation." *arXiv:2603.00077*.
- Langfuse. "LLM-as-a-Judge." *docs.langfuse.com/docs/scores/evals*.
- Daynauth, R. et al. (2025). "Ranking Unraveled: Recipes for LLM Rankings in Head-to-Head AI Combat." *ACL 2025*.
- Son, S. et al. (2024). "Varco Arena: A Tournament Approach to Reference-Free Benchmarking Large Language Models." *arXiv:2411.01281*.

### Requirements Engineering & NLP
- Gnesi, S. & Trentanni, G. (2019). "QuARS: a NLP tool for requirements analysis." *ISTI-CNR*.
- Rosadini, B. et al. (2017). "Using NLP to Detect Requirements Defects: an Industrial Experience in the Railway Domain." *ISTI-CNR*.
- Senk, D. & Kroha, P. (2023). "Quality Measurement of Functional Requirements." *SCITEPRESS*.
- Gramajo, M.G. et al. (2021). "Recurrent Neural Networks to automate Quality assessment of Software Requirements." *arXiv:2105.04757*.
- Bankauskaite, J. & Morkevicius, A. (2018). "SysML-based Automated Completeness Evaluation of the System Requirements Specification." *CEUR-WS*.
- Ponnusamy, A. (2025). "Bridging LLM-Generated Code and Requirements: Reverse Generation technique and SBC Metric." *arXiv:2502.07835*.
- Lourenço, L.M. et al. (2025). "Quality Evaluation of Software Functional Requirements Generated by LLMs: A Systematic Mapping Study." *SBSI*.

### Modernisation Methodology
- SpecOps Method. "A Specification-Driven Approach to Legacy System Modernization." *github.com/spec-ops-method/spec-ops*.
- Catalio. "Gap Analysis & Risk-Free Modernization." *catalio.ai/docs/gap-analysis*.
- ARDURA Consulting. "Legacy System Modernization Checklist: Assessment to Execution." *ardura.consulting/blog*.
- DLA (2017). "Requirements Traceability Verification Matrix (RTVM)." *DI-MGMT-82133*.

### Government & Enterprise AI
- World Economic Forum (2026). "Making Agentic AI Work for Government: A Readiness Framework."
- AEEF. "AI Agent SDLC Orchestration." *aeef.ai/transformation/agent-sdlc-orchestration*.

---

*Report generated 2026-04-30 by Devin for the ifactorial autoresearch workspace.*
*Methodology: web research synthesis across 25+ academic papers, industry reports, and open-source projects.*
