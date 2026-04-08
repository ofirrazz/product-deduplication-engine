"""Group duplicate product listings and surface the minimum price per logical product."""

from __future__ import annotations

from collections import defaultdict

from matcher import match_key, representative_name
from models import Product, UnifiedProduct


def deduplicate(products: list[Product]) -> list[UnifiedProduct]:
    """
    Cluster products by matcher.match_key and keep the lowest price per cluster.

    Future: merge clusters using transitive closure over fuzzy/embedding similarity,
    or run a two-stage pipeline (blocking + expensive pairwise scoring).
    """
    clusters: dict[str, list[Product]] = defaultdict(list)
    for p in products:
        clusters[match_key(p.name)].append(p)

    unified: list[UnifiedProduct] = []
    for key, group in sorted(clusters.items(), key=lambda kv: kv[0]):
        names = [p.name for p in group]
        min_p = min(group, key=lambda x: x.price)
        unified.append(
            UnifiedProduct(
                canonical_name=representative_name(names),
                min_price=min_p.price,
                currency=min_p.currency,
                product_ids=tuple(sorted(p.id for p in group)),
                raw_names=tuple(names),
            )
        )
    return unified
