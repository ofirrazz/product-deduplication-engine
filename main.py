"""CLI entry: load sample products, deduplicate, print unified rows with minimum price."""

from __future__ import annotations

import sys

from deduplicator import deduplicate

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from sample_data import sample_products


def main() -> None:
    products = sample_products()
    unified = deduplicate(products)

    print("Unified products (lowest price per group)\n")
    for u in unified:
        print(f"  Display: {u.canonical_name}")
        print(f"  Min price: {u.min_price:.2f} {u.currency}")
        print(f"  Merged IDs: {', '.join(u.product_ids)}")
        print(f"  Raw names seen: {u.raw_names}")
        print()


if __name__ == "__main__":
    main()
