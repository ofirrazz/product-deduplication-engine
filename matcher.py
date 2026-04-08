"""Compute a stable key so different spellings/orderings of the same product group together."""

from __future__ import annotations

from normalizer import normalize_text

# Optional token aliases after normalization (e.g. model codes written different ways).
# Future: learn aliases from data, or replace with embedding nearest-neighbor keys.
_TOKEN_ALIASES: dict[str, str] = {
    "23s": "s23",
    "s23": "s23",
    "15pro": "15 pro",
}


def _canonical_tokens(normalized: str) -> tuple[str, ...]:
    if not normalized:
        return ()
    parts = normalized.split()
    out: list[str] = []
    for p in parts:
        canon = _TOKEN_ALIASES.get(p, p)
        out.append(canon)
    return tuple(sorted(out))


def match_key(name: str) -> str:
    """
    Map a raw product name to a grouping key.

    Current approach: normalize text, then sort tokens so word order does not split groups.

    Future extension points (swap implementation behind this function):
    - Fuzzy string match (RapidFuzz, Levenshtein) against a canonical catalog.
    - Dense embeddings + cosine similarity + clustering (e.g. sentence-transformers).
    - LLM-based "same SKU?" with a cached verdict per pair or per cluster.
    """
    n = normalize_text(name)
    tokens = _canonical_tokens(n)
    return " ".join(tokens) if tokens else n


def representative_name(names: list[str]) -> str:
    """Pick a display name for a cluster (shortest cleaned raw name, stable tie-break)."""
    if not names:
        return ""
    return min(names, key=lambda x: (len(x.strip()), x))
