"""D6: Consistency — are there internal contradictions?

Deterministic checks:
- Terminology consistency (same term used the same way throughout)
- Keyword conflicts (SHALL vs SHALL NOT on same entity)
- Duplicate/conflicting requirements
- Cross-reference integrity
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict

from speceval.schema import (
    Diagnostic,
    Dimension,
    DimensionScore,
    EvalInput,
    Severity,
)


def _extract_defined_terms(markdown: str) -> dict[str, list[str]]:
    """Extract terms from glossary/definitions sections."""
    terms: dict[str, list[str]] = {}
    in_glossary = False
    for line in markdown.split("\n"):
        if re.match(r"^#{1,6}\s+.*(glossar|definition|terminolog|acronym)", line, re.IGNORECASE):
            in_glossary = True
            continue
        if in_glossary and re.match(r"^#{1,6}\s+", line):
            in_glossary = False
            continue
        if in_glossary:
            # Match "**Term** — definition" or "- Term: definition"
            m = re.match(r"(?:\*\*(.+?)\*\*|[-*]\s*(.+?))\s*[—:\-]\s*(.+)", line)
            if m:
                term = (m.group(1) or m.group(2)).strip()
                defn = m.group(3).strip()
                terms.setdefault(term.lower(), []).append(defn)
    return terms


def _find_keyword_conflicts(markdown: str) -> list[tuple[str, str, str]]:
    """Find cases where SHALL and SHALL NOT apply to the same subject, or
    where requirements directly contradict each other semantically."""
    conflicts: list[tuple[str, str, str]] = []

    # Pattern 1: Explicit SHALL vs SHALL NOT on same subject
    shall_pattern = re.compile(
        r"(?:the\s+)?(\w+(?:\s+\w+)?)\s+(shall|must)\s+(.+?)(?:\.|$)",
        re.IGNORECASE | re.MULTILINE,
    )
    shall_not_pattern = re.compile(
        r"(?:the\s+)?(\w+(?:\s+\w+)?)\s+(shall not|must not)\s+(.+?)(?:\.|$)",
        re.IGNORECASE | re.MULTILINE,
    )

    positives = defaultdict(list)
    negatives = defaultdict(list)

    for m in shall_pattern.finditer(markdown):
        subject = m.group(1).lower()
        action = m.group(3).strip()[:80]
        positives[subject].append(action)

    for m in shall_not_pattern.finditer(markdown):
        subject = m.group(1).lower()
        action = m.group(3).strip()[:80]
        negatives[subject].append(action)

    for subject in positives:
        if subject in negatives:
            for pos in positives[subject]:
                for neg in negatives[subject]:
                    pos_words = set(pos.lower().split())
                    neg_words = set(neg.lower().split())
                    overlap = len(pos_words & neg_words) / max(len(pos_words | neg_words), 1)
                    if overlap > 0.3:  # Lower threshold to catch more
                        conflicts.append((subject, pos, neg))

    # Pattern 2: Direct semantic contradictions across ALL requirements
    # Look for pairs where one says "do X" and another says "not do X"
    all_reqs: list[tuple[str, str]] = []  # (full_match, action_text)
    for m in shall_pattern.finditer(markdown):
        all_reqs.append((m.group(0).strip(), m.group(3).strip()[:80]))
    for m in shall_not_pattern.finditer(markdown):
        all_reqs.append((m.group(0).strip(), "NOT " + m.group(3).strip()[:80]))

    # Check for topic contradictions (e.g., "use LDAP exclusively" vs "migrate away from LDAP")
    for i, (req_a, act_a) in enumerate(all_reqs):
        for j, (req_b, act_b) in enumerate(all_reqs):
            if j <= i:
                continue
            # Check if one is positive and one is negative about same topic
            a_words = set(re.findall(r"\b\w{4,}\b", act_a.lower()))
            b_words = set(re.findall(r"\b\w{4,}\b", act_b.lower()))
            common = a_words & b_words
            if len(common) >= 2:  # Share meaningful terms
                a_negated = "not" in act_a.lower() or "NOT " in act_a
                b_negated = "not" in act_b.lower() or "NOT " in act_b
                if a_negated != b_negated:
                    conflicts.append(("(cross-req)", req_a[:60], req_b[:60]))

    return conflicts


def _find_duplicate_requirements(markdown: str) -> list[tuple[str, str]]:
    """Find suspiciously similar requirement statements."""
    req_pattern = re.compile(
        r"(?:shall|must|will)\s+(.{20,100}?)(?:\.|$)",
        re.IGNORECASE | re.MULTILINE,
    )
    reqs = [m.group(1).strip().lower() for m in req_pattern.finditer(markdown)]

    duplicates: list[tuple[str, str]] = []
    seen: dict[str, str] = {}
    for req in reqs:
        # Normalise whitespace
        normalised = " ".join(req.split())
        # Check for near-duplicates using word overlap
        for existing_norm, existing_orig in seen.items():
            words_a = set(normalised.split())
            words_b = set(existing_norm.split())
            if not words_a or not words_b:
                continue
            overlap = len(words_a & words_b) / max(len(words_a | words_b), 1)
            if overlap > 0.8 and normalised != existing_norm:
                duplicates.append((existing_orig, req))
                break
        seen[normalised] = req

    return duplicates


def evaluate_consistency(eval_input: EvalInput) -> DimensionScore:
    """Evaluate D6: Consistency."""
    markdown = eval_input.generated_spec.markdown
    diagnostics: list[Diagnostic] = []
    sub_scores: dict[str, float] = {}

    # 1. Keyword conflicts
    conflicts = _find_keyword_conflicts(markdown)
    conflict_score = max(0.0, 1.0 - len(conflicts) * 0.25)
    sub_scores["no_keyword_conflicts"] = conflict_score
    for subj, pos, neg in conflicts[:5]:
        diagnostics.append(Diagnostic(
            dimension=Dimension.CONSISTENCY,
            severity=Severity.CRITICAL,
            message=f"Contradictory requirements for '{subj}': SHALL '{pos}' vs SHALL NOT '{neg}'",
        ))

    # 2. Duplicate requirements
    duplicates = _find_duplicate_requirements(markdown)
    dup_score = max(0.0, 1.0 - len(duplicates) * 0.15)
    sub_scores["no_duplicates"] = dup_score
    for orig, dup in duplicates[:5]:
        diagnostics.append(Diagnostic(
            dimension=Dimension.CONSISTENCY,
            severity=Severity.MINOR,
            message=f"Possible duplicate requirement: '{dup[:60]}'",
            evidence=f"Similar to: '{orig[:60]}'",
        ))

    # 3. Terminology consistency
    defined_terms = _extract_defined_terms(markdown)
    multi_def = {t: defs for t, defs in defined_terms.items() if len(defs) > 1}
    term_score = max(0.0, 1.0 - len(multi_def) * 0.20)
    sub_scores["terminology_consistency"] = term_score
    for term, defs in list(multi_def.items())[:3]:
        diagnostics.append(Diagnostic(
            dimension=Dimension.CONSISTENCY,
            severity=Severity.MAJOR,
            message=f"Term '{term}' has multiple definitions",
            evidence=f"Definitions: {defs[:2]}",
        ))

    # 4. Cross-reference integrity (check for broken internal links)
    link_pattern = re.compile(r"\[([^\]]+)\]\(#([^)]+)\)")
    headings_lower = {
        re.sub(r"[^a-z0-9-]", "", h.lower().replace(" ", "-"))
        for h in re.findall(r"^#{1,6}\s+(.+)$", markdown, re.MULTILINE)
    }
    broken_links = []
    for m in link_pattern.finditer(markdown):
        anchor = m.group(2).lower()
        if anchor not in headings_lower:
            broken_links.append((m.group(1), anchor))
    xref_score = max(0.0, 1.0 - len(broken_links) * 0.10)
    sub_scores["xref_integrity"] = xref_score
    for label, anchor in broken_links[:5]:
        diagnostics.append(Diagnostic(
            dimension=Dimension.CONSISTENCY,
            severity=Severity.MINOR,
            message=f"Broken internal link: [{label}](#{anchor})",
        ))

    # Composite
    weights = {
        "no_keyword_conflicts": 0.35,
        "no_duplicates": 0.25,
        "terminology_consistency": 0.25,
        "xref_integrity": 0.15,
    }
    score = sum(weights[k] * sub_scores[k] for k in weights)

    return DimensionScore(
        dimension=Dimension.CONSISTENCY,
        score=score,
        confidence=1.0,
        details={"sub_scores": sub_scores},
        diagnostics=diagnostics,
    )
