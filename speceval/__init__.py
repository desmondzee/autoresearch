"""speceval — SOTA benchmark for agentic specification generation pipelines.

Architecture-agnostic eval framework inspired by Karpathy's autoresearch loop:
  1. Define inputs (source docs, templates, goals)
  2. Run the pipeline under test → generated spec
  3. Evaluate across 8 quality dimensions (Tier 1 deterministic + Tier 2 LLM-as-judge)
  4. RALPH loop: Research → Assess → Learn → Plan → Harden
  5. Log results, keep or discard, repeat
"""

__version__ = "0.1.0"
