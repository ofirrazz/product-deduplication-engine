# Product deduplication (e-commerce)

This project demonstrates a practical, production-oriented approach to product matching in noisy e-commerce environments.

## Problem

Marketplaces list the same sellable unit under many titles and feeds. The goal is a **generic** matcher that works across categories (phones, TVs, laptops, appliances, etc.), prefers **catalog identifiers** when they are trustworthy, and otherwise uses **deterministic normalization + extracted attributes + a conservative fuzzy layer**. Each unified product shows the **lowest** price in its cluster. **The same pipeline applies across categories such as phones, TVs, laptops, and appliances without changing the core logic.**

## Design Philosophy

- **Conservative by design:** feeds and seller titles are noisy; the pipeline assumes ambiguity is normal.  
- **Precision over recall:** we prefer leaving a near-duplicate visible over collapsing two distinct SKUs.  
- **Operational reality:** in e-commerce, a bad merge tends to cost more than a missed duplicate (pricing errors, fulfillment risk, support load), so defaults favor separation.

## Matching priority (identifier-first)

1. **Strong identifiers (trusted)**  
   - **GTIN / EAN / UPC**: digits-only, lengths 8/12/13/14. The model accepts `gtin`, `ean`, or `upc`; the first valid barcode wins.  
   - **MPN + brand**: normalized manufacturer part number (hyphens stripped) with a brand token.  
   - The key includes `key_for_strong_catalog_id` (storage / year / screen size / edition). **Color is omitted** here: different finishes usually ship under different barcodes/MPNs.

2. **Weak SKU**  
   Normalized seller `sku` + full variant fingerprint (includes color).

3. **Text**  
   Strict key: sorted family tokens + full variant fingerprint.

4. **Fuzzy text (RapidFuzz)** — *only if step 3 applies*  
   Within one **variant fingerprint bucket**, `token_sort_ratio` merges obvious typos / reorderings.  
   **Never** compares rows across different variant keys. **Never** runs when a strong ID or weak SKU path matched.  
   **RapidFuzz** is used because it is **fast**, produces **stable, deterministic** scores for a given input pair, and fits **token-oriented** similarity well—aligned with normalized word bags rather than free-form prose semantics.

Guards (see `fuzzy_match.py`): fuzzy pairing runs only when **both** family fingerprints are “meaningful” (default: **≥2 tokens** and **≥8 non-space characters**). Short/noisy labels keep the strict `text|family|...` key instead of joining a fuzzy component.

The default cutoff is **95.0** (`FUZZY_TOKEN_SORT_MIN_SCORE`), chosen so many “almost same” model lines (e.g. **Galaxy S23 vs S24** ~94.4) stay split while typical retailer typos still merge. Override via `deduplicate(..., fuzzy_threshold=...)`. You can also tune `fuzzy_min_family_tokens` and `fuzzy_min_family_char_nospace` passed through to `assign_text_fuzzy_keys`.

Fuzzy cluster keys use the **most informative** canonical family label (more tokens / digits / length), not the lexicographically smallest string—ties break on the label text for stability.

This stays **operationally deterministic**: fixed pipeline, fixed threshold (`FUZZY_TOKEN_SORT_MIN_SCORE` in `fuzzy_match.py`), and a pinned RapidFuzz version in `requirements.txt`. The only “floating” piece is the fuzzy library’s implementation version—acceptable to mention explicitly in interviews.

## Generic normalization (`normalizer.py`)

Composable steps (in order):

- Unicode **NFKC**
- Lowercase
- Double-quote **inch** marks → `inch` token
- **Compact** number+unit: `256 gb`→`256gb`, `1 tb`→`1tb`, `15.6 inch`→`15.6inch`
- Split glued editions (`15pro`→`15 pro`)
- **Small Hebrew commerce glossary** (units, colors, editions, a few generic words like `טלוויזיה`→`tv`) — helper only, not the core strategy
- **Galaxy S-line helpers (guarded):** if the normalized title contains `samsung` or `galaxy`, apply (1) inverted `NNs`→`sNN` for two-digit tokens, e.g. `23s samsung`→`s23 samsung`, and (2) a small set of **regex** folds so permutations like `s23 samsung` align with `samsung s23`—no per-model dictionary. Titles without that context skip these rules to avoid touching unrelated `NNs` tokens.
- **Tiny typo / phrase fixes** (e.g. `whirpool`→`whirlpool`, `stainless steel`→`stainless`) — keep this list small; fix upstream feeds when possible
- Punctuation → spaces, whitespace collapse

`matcher.py` also drops generic **noise tokens** from the family fingerprint (`laptop`, `smart`, `wifi`, …) so “ThinkPad X1 Carbon laptop” and “ThinkPad X1 Carbon” align without hiding real model tokens.

## Why Not a Large Dictionary?

The engine does **not** hinge on a large, hand-maintained alias map. Matching is driven mainly by **structural normalization** (units, punctuation, token shape), **attribute extraction** (storage, size, year, color, editions), and **bounded fuzzy similarity** on text-only rows with strict guards. That combination **generalizes across product types** and stays cheaper to own than expanding synonym tables for every category and locale.

## Attribute extraction

From the normalized title:

- Storage (`Ngb`, `Ntb`)
- Four-digit **calendar** year (when present)
- Display size (`Ninch` → canonical `Nin` for the variant key)
- Color phrases (longest match wins)
- Edition tokens: `pro`, `max`, `plus`, `ultra`

Variant attributes feed both **strict keys** and **fuzzy buckets**.

## Project structure

| File | Role |
|------|------|
| `main.py` | Sample runner |
| `models.py` | `Product`, `VariantAttributes`, `ProductSignature`, `UnifiedProduct` |
| `normalizer.py` | Step-wise normalization + extractors |
| `matcher.py` | Identifier-first keys, family fingerprints, display title |
| `fuzzy_match.py` | RapidFuzz clustering for text-only rows (variant-scoped) |
| `deduplicator.py` | Applies fuzzy map, merges clusters, min price, currency guard |
| `sample_data.py` | Multi-category demo rows |
| `requirements.txt` | `rapidfuzz` |

## Install & run

```bash
pip install -r requirements.txt
python main.py
```

On Windows, `main.py` sets UTF-8 on stdout for Hebrew in the console.

## Conservative guarantees

- Mixed **currencies** in one cluster → `CurrencyConflictError`
- Different **variant fingerprints** → never merged by fuzzy
- **Pro Max** vs **Pro** stays separate via edition tokens
- **Color** participates in text/SKU keys (not in strong barcode fingerprint)

## Limitations and tradeoffs

- The design stays **generic and category-agnostic**; it will not capture every vendor-specific naming quirk without extension.  
- **Noisy retail copy** sometimes needs **small, explicit normalization rules** rather than a giant dictionary.  
- **Samsung Galaxy S-series** style listings illustrate the pattern: inverted tokens such as `23S Samsung` are corrected with **minimal regex** (scoped behind a `samsung`/`galaxy` check) in `normalizer.py`—not a hardcoded catalog of model IDs.  
- Those exceptions are **narrow on purpose**: they improve a high-impact product family without turning the matcher into a single-brand special case.

## Optional domain-specific enhancements

In a production deployment, it is reasonable to add **occasional, data-backed rules** for families that dominate volume or margin—still preferably **regex or grammar-shaped**, each with tests and owners. The bar should stay high: every addition should prove lift in real data; otherwise the codebase drifts toward an unmaintainable synonym layer.

## Future improvements

- **Embedding-based similarity** for titles that describe the same SKU with different vocabulary (with tight calibration and review hooks).  
- **Canonical catalog integration** (e.g. **MPN → structured attributes**) so identifiers and attributes anchor the record and titles are secondary.  
- **Category-specific extractors** behind the same interfaces (appliances, apparel, etc.).  
- **Cross-currency price normalization** where listings mix markets (FX, tax-included vs excluded, rounding).  
- **Per-cluster or per-edge confidence scores** to route borderline matches to human review or stricter policies.
