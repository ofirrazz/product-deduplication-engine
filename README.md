# Product deduplication (e-commerce)

## Problem

Suppliers and marketplaces expose the same physical product under many strings: different languages, word order, spacing, and typos. Customers should see **one** logical product with the **lowest** available price across merged listings.

## Approach

1. **Normalize** names with simple, deterministic rules (case, spacing, Hebrew glosses for common terms).
2. **Match** listings to a grouping key (today: normalized tokens, sorted, with a small alias map for obvious model-code variants).
3. **Deduplicate** by cluster: keep the minimum price and a human-friendly display name.

This skeleton is intentionally easy to extend: swap `match_key()` for fuzzy or embedding-based similarity without changing the pipeline shape.

## Project structure

| File | Role |
|------|------|
| `main.py` | Runs the sample pipeline and prints results |
| `models.py` | `Product` and `UnifiedProduct` dataclasses |
| `normalizer.py` | Rule-based string normalization |
| `matcher.py` | Grouping key + display-name pick; hooks for ML later |
| `deduplicator.py` | Cluster by key, compute min price per cluster |
| `sample_data.py` | Messy duplicate examples (EN + HE) |

## How to run

```bash
python main.py
```

(No third-party packages required for the baseline.)

## Example output

```
Unified products (lowest price per group)

  Display: Pro 15 iPhone
  Min price: 4100.00 ILS
  Merged IDs: p6, p7, p8, p9
  Raw names seen: ('iPhone 15 Pro', 'IPHONE 15 PRO 256GB', 'אייפון 15 פרו', 'Pro 15 iPhone')

  Display: 23S Samsung
  Min price: 2700.00 ILS
  Merged IDs: p1, p2, p3, p4, p5
  Raw names seen: ('Samsung Galaxy S23', '  samsung   galaxy s23', 'סמסונג גלקסי S23', ...)

  Display: Samsung Galaxy S24
  Min price: 3200.00 ILS
  Merged IDs: p10
  Raw names seen: ('Samsung Galaxy S24',)
```

On Windows, `main.py` sets UTF-8 on stdout so Hebrew characters print correctly in the console.

The **display** line is the shortest raw name in the cluster (see `representative_name` in `matcher.py`).
