"""Group duplicate product listings and surface the minimum price per logical product."""

from __future__ import annotations

from collections import defaultdict

from fuzzy_match import (
    FUZZY_MIN_FAMILY_CHAR_NO_SPACE,
    FUZZY_MIN_FAMILY_TOKENS,
    FUZZY_TOKEN_SORT_MIN_SCORE,
    assign_text_fuzzy_keys,
)
from matcher import build_signature, representative_name
from models import Product, UnifiedProduct


class CurrencyConflictError(ValueError):
    """Raised when a dedupe cluster contains more than one currency."""


def deduplicate(
    products: list[Product],
    *,
    fuzzy_threshold: float = FUZZY_TOKEN_SORT_MIN_SCORE,
    fuzzy_min_family_tokens: int = FUZZY_MIN_FAMILY_TOKENS,
    fuzzy_min_family_char_nospace: int = FUZZY_MIN_FAMILY_CHAR_NO_SPACE,
) -> list[UnifiedProduct]:
    """
    Cluster listings: identifier-first strict keys, then conservative fuzzy regrouping
    for text-only rows with compatible variant fingerprints.

    Fuzzy knobs apply only to text-tier products (see ``assign_text_fuzzy_keys``).
    """
    fuzzy_map = assign_text_fuzzy_keys(
        products,
        fuzzy_threshold=fuzzy_threshold,
        min_family_tokens=fuzzy_min_family_tokens,
        min_family_char_nospace=fuzzy_min_family_char_nospace,
    )

    clusters: dict[str, list[Product]] = defaultdict(list)
    for p in products:
        sig = build_signature(p)
        if sig.match_tier == "text":
            key = fuzzy_map[p.id]
        else:
            key = sig.dedupe_key
        clusters[key].append(p)

    unified: list[UnifiedProduct] = []
    for key in sorted(clusters.keys()):
        group = sorted(clusters[key], key=lambda x: x.id)
        currencies = {p.currency for p in group}
        if len(currencies) > 1:
            ids = ", ".join(p.id for p in group)
            raise CurrencyConflictError(
                f"Cluster {key!r} mixes currencies {sorted(currencies)!r}; product ids: {ids}"
            )

        sig0 = build_signature(group[0])
        tier = "text_fuzzy" if key.startswith("text|fuzzy|") else sig0.match_tier
        variant = sig0.variant
        names = [p.name for p in group]
        min_p = min(group, key=lambda x: x.price)
        unified.append(
            UnifiedProduct(
                canonical_name=representative_name(group, variant),
                min_price=min_p.price,
                currency=min_p.currency,
                dedupe_key=key,
                match_tier=tier,
                family_key=sig0.family_key,
                variant_key=variant.key,
                product_ids=tuple(p.id for p in group),
                raw_names=tuple(names),
            )
        )
    return unified
