"""
Conservative fuzzy clustering for text-only listings (RapidFuzz).

**Why text tier only:** rows with GTIN/MPN/SKU already have a strict key; fuzzy similarity is
for noisy titles without a trusted identifier—running it on ID-backed rows would risk
over-merging unrelated SKUs that share boilerplate.

**Why same variant fingerprint:** fuzzy compares family strings only inside one ``variant.key``
bucket so storage/color/size/edition mismatches never get a similarity pass.

Meaningful-label guards (token count + length) and ``fuzzy_threshold`` stay configurable.
"""

from __future__ import annotations

from collections import defaultdict

from rapidfuzz import fuzz

from matcher import build_signature, family_compare_string
from models import Product
from normalizer import extract_variant_attributes

# Default similarity floor (0–100). Tuned so near models like S23 vs S24 (~94.4) stay split at 95.
# Override per call: ``deduplicate(..., fuzzy_threshold=...)`` or pass into ``assign_text_fuzzy_keys``.
FUZZY_TOKEN_SORT_MIN_SCORE: float = 95.0
FUZZY_MIN_FAMILY_TOKENS: int = 2
FUZZY_MIN_FAMILY_CHAR_NO_SPACE: int = 8


class _UnionFind:
    __slots__ = ("parent", "rank")

    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, i: int) -> int:
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, i: int, j: int) -> None:
        ri, rj = self.find(i), self.find(j)
        if ri == rj:
            return
        if self.rank[ri] < self.rank[rj]:
            self.parent[ri] = rj
        elif self.rank[ri] > self.rank[rj]:
            self.parent[rj] = ri
        else:
            self.parent[rj] = ri
            self.rank[ri] += 1


def _safe_key_token(text: str) -> str:
    return text.replace("|", " ").strip()


def _family_label_meaningful(
    label: str,
    *,
    min_tokens: int,
    min_char_nospace: int,
) -> bool:
    parts = label.split()
    if len(parts) < min_tokens:
        return False
    compact = label.replace(" ", "")
    if len(compact) < min_char_nospace:
        return False
    return True


def _best_canonical_family_label(labels: list[str]) -> str:
    """
    Pick the most informative family fingerprint for a fuzzy cluster (deterministic).

    Prefers more tokens, more digits, longer compact length; breaks ties lexicographically.
    """

    def sort_key(lab: str) -> tuple[int, int, int, str]:
        toks = len(lab.split())
        digits = sum(1 for c in lab if c.isdigit())
        compact_len = len(lab.replace(" ", ""))
        return (-toks, -digits, -compact_len, lab)

    return min(labels, key=sort_key)


def assign_text_fuzzy_keys(
    products: list[Product],
    *,
    fuzzy_threshold: float = FUZZY_TOKEN_SORT_MIN_SCORE,
    min_family_tokens: int = FUZZY_MIN_FAMILY_TOKENS,
    min_family_char_nospace: int = FUZZY_MIN_FAMILY_CHAR_NO_SPACE,
) -> dict[str, str]:
    """
    Map product.id -> final dedupe key for text-tier rows.

    - Meaningless short labels skip fuzzy pairing and keep the strict ``text|family|...`` key.
    - Meaningful labels cluster with ``token_sort_ratio`` >= ``fuzzy_threshold``.
    - Canonical key token is the most informative label in the cluster (not lexicographic min).
    """
    # Snapshot text-tier rows only; identifier-backed products keep strict keys unchanged.
    text_products: list[Product] = []
    for p in products:
        sig = build_signature(p)
        if sig.match_tier == "text":
            text_products.append(p)

    result: dict[str, str] = {}
    if not text_products:
        return result

    # Partition by variant fingerprint so fuzzy never crosses storage/color/size/year/edition.
    buckets: dict[str, list[Product]] = defaultdict(list)
    for p in text_products:
        vkey = extract_variant_attributes(p.name).key
        buckets[vkey].append(p)

    for vkey in sorted(buckets.keys()):
        group = sorted(buckets[vkey], key=lambda x: x.id)
        labels = [family_compare_string(p) for p in group]
        meaningful = [
            _family_label_meaningful(
                lab,
                min_tokens=min_family_tokens,
                min_char_nospace=min_family_char_nospace,
            )
            for lab in labels
        ]
        n = len(group)

        for i in range(n):
            if not meaningful[i]:
                result[group[i].id] = build_signature(group[i]).dedupe_key

        eligible_idx = [i for i in range(n) if meaningful[i]]
        if not eligible_idx:
            continue

        k = len(eligible_idx)
        uf = _UnionFind(k)
        for ai in range(k):
            for bi in range(ai + 1, k):
                i = eligible_idx[ai]
                j = eligible_idx[bi]
                if fuzz.token_sort_ratio(labels[i], labels[j]) >= fuzzy_threshold:
                    uf.union(ai, bi)

        root_to_members: dict[int, list[int]] = defaultdict(list)
        for ai in range(k):
            root_to_members[uf.find(ai)].append(ai)

        for members_ai in sorted(root_to_members.values(), key=lambda xs: min(xs)):
            global_indices = [eligible_idx[ai] for ai in members_ai]
            cluster_labels = [labels[g] for g in global_indices]
            canonical = _safe_key_token(_best_canonical_family_label(cluster_labels))
            final_key = f"text|fuzzy|{canonical}|{vkey}"
            for g in global_indices:
                result[group[g].id] = final_key

    return result
