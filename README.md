# Product deduplication (e-commerce)

## Problem

Marketplaces list the same sellable unit under many titles and feeds. The goal is a **generic** matcher that works across categories (phones, TVs, laptops, appliances, etc.), prefers **catalog identifiers** when they are trustworthy, and otherwise uses **deterministic normalization + extracted attributes + a conservative fuzzy layer**. Each unified product shows the **lowest** price in its cluster. **The same pipeline applies across categories such as phones, TVs, laptops, and appliances without changing the core logic.**

## Design Philosophy

- The system is **intentionally conservative**: it assumes catalog and title data are noisy.  
- It **prefers avoiding false positives over maximizing recall**—merging the wrong offers is worse than showing a few extra rows.  
- In e-commerce, **incorrect merges are typically more harmful than missing duplicates** (wrong price, wrong SKU, customer complaints), so the defaults err on the side of separation.

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
- **Inverted model token** `NNs`→`sNN` via regex (two-digit slice), e.g. `23s samsung`→`s23 samsung`
- **Minimal Samsung + Galaxy + `s<number>` permutations** folded to `samsung s<number>` (regex only; no per-model dictionary)
- **Tiny typo / phrase fixes** (e.g. `whirpool`→`whirlpool`, `stainless steel`→`stainless`) — keep this list small; fix upstream feeds when possible
- Punctuation → spaces, whitespace collapse

`matcher.py` also drops generic **noise tokens** from the family fingerprint (`laptop`, `smart`, `wifi`, …) so “ThinkPad X1 Carbon laptop” and “ThinkPad X1 Carbon” align without hiding real model tokens.

## Why Not a Large Dictionary?

This project does **not** rely on a large, manually curated synonym dictionary as the main matching strategy. Instead, it leans on **structural normalization** (units, punctuation, word order) and **attribute extraction** (storage, size, year, color, editions) to separate variants and build keys. That approach **scales across categories** with less ongoing maintenance than growing an exhaustive term list per vertical.

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

The matcher stays **intentionally generic** and does **not** depend on a large alias dictionary. That keeps maintenance low and behavior predictable across categories, but **some noisy retail patterns need small, targeted normalization rules**—for example inverted `NNs` tokens and a compact set of **Samsung + Galaxy + `s\\d` word-order folds** implemented as **regex** in `normalizer.py`, not as a model-by-model lookup. Those rules are **minimal** so we do not overfit the whole stack to one OEM.

### Optional domain-specific enhancements

In production, teams sometimes add **a few high-impact, well-scoped rules** for families that drive most revenue (still regex- or grammar-based where possible). The goal is to stay **small and testable**: each rule should have clear acceptance tests and be removable if the feed quality improves—avoid turning the engine into an unmaintainable synonym table.

## Future Improvements

- **Embedding-based similarity** for semantic matching when titles diverge but mean the same SKU (with careful calibration to avoid over-merging).  
- **Integration with a canonical product catalog** (e.g. resolve **MPN → structured attributes**) so titles become hints, not the sole source of truth.  
- **Category-specific extractors** (e.g. appliances vs wearables) plugged into the same pipeline behind stable interfaces.  
- **Cross-currency price normalization** for international feeds (FX rates, tax-inclusive vs exclusive, rounding rules).  
- **Confidence scoring** for each match tier (identifier vs fuzzy vs text) to drive review queues and auto-merge policies.
