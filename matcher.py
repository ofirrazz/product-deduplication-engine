"""
Identifier-first dedupe keys, family fingerprints, and display-friendly representative titles.

Strong IDs and weak SKUs are authoritative; text tier may be refined later by ``fuzzy_match``
(never changing identifier precedence or variant boundaries).
"""

from __future__ import annotations

import re
from typing import Optional

from models import Product, ProductSignature, VariantAttributes
from normalizer import extract_variant_attributes, normalize_text, remove_variant_tokens

_TOKEN_ALIASES: dict[str, str] = {}

# Generic title fluff (still appears in raw display names; excluded from family fingerprints).
_FAMILY_NOISE_TOKENS: frozenset[str] = frozenset(
    {
        "laptop",
        "notebook",
        "computer",
        "pc",
        "wifi",
        "cellular",
        "unlocked",
        "new",
        "renewed",
        "smart",
        "tv",
    }
)


def _digits_only(value: str) -> str:
    return re.sub(r"\D+", "", value)


def _normalize_barcode(*candidates: Optional[str]) -> Optional[str]:
    """GTIN / EAN / UPC: keep digits only; accept common retail lengths."""
    for raw in candidates:
        if not raw:
            continue
        digits = _digits_only(raw)
        if len(digits) in (8, 12, 13, 14):
            return digits
    return None


def _normalize_mpn(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    compact = re.sub(r"\s+", "", raw.strip().lower())
    compact = compact.replace("-", "")
    if len(compact) < 2:
        return None
    return compact


def _normalize_sku(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    compact = re.sub(r"\s+", "", raw.strip().lower())
    return compact or None


def _normalize_brand_token(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    token = normalize_text(raw).replace(" ", "")
    return token or None


def _family_token_tuple(name: str, brand: Optional[str]) -> tuple[str, ...]:
    normalized = normalize_text(name)
    base = remove_variant_tokens(normalized)
    parts = base.split()
    brand_token = _normalize_brand_token(brand)
    if brand_token:
        parts = [p for p in parts if p != brand_token]
        parts = [brand_token] + parts
    parts = [p for p in parts if p not in _FAMILY_NOISE_TOKENS and p not in {"-", ".", "_"}]
    canon = [_TOKEN_ALIASES.get(p, p) for p in parts if p]
    return tuple(sorted(canon))


def family_key_from_product(product: Product) -> str:
    """Stable pipe-joined family token string (sorted, noise-stripped) for strict text keys."""
    return "|".join(_family_token_tuple(product.name, product.brand)) or "unknown"


def family_compare_string(product: Product) -> str:
    """Space-separated, order-invariant fingerprint for fuzzy similarity."""
    return " ".join(_family_token_tuple(product.name, product.brand))


def _variant_from_product(product: Product) -> VariantAttributes:
    return extract_variant_attributes(product.name)


def _strong_identifier_key(product: Product, variant: VariantAttributes) -> Optional[tuple[str, str]]:
    barcode = None
    if product.gtin_trusted:
        barcode = _normalize_barcode(product.gtin, product.ean, product.upc)
    if barcode:
        return (f"strong|gtin|{barcode}|{variant.key_for_strong_catalog_id}", "strong_id")

    mpn = _normalize_mpn(product.mpn) if product.mpn_trusted else None
    if mpn:
        brand = _normalize_brand_token(product.brand) or "nobrand"
        return (f"strong|mpn|{brand}|{mpn}|{variant.key_for_strong_catalog_id}", "strong_id")

    return None


def _weak_sku_key(product: Product, variant: VariantAttributes) -> Optional[str]:
    sku = _normalize_sku(product.sku)
    if not sku:
        return None
    return f"weak|sku|{sku}|{variant.key}"


def _text_strict_key(product: Product, variant: VariantAttributes) -> str:
    family = family_key_from_product(product)
    return f"text|family|{family}|{variant.key}"


def build_signature(product: Product) -> ProductSignature:
    """Strict, identifier-first signature (text rows may be regrouped later by fuzzy_match)."""
    variant = _variant_from_product(product)
    strong = _strong_identifier_key(product, variant)
    if strong:
        key, tier = strong
        return ProductSignature(
            dedupe_key=key,
            family_key=family_key_from_product(product),
            variant=variant,
            match_tier=tier,
        )

    weak = _weak_sku_key(product, variant)
    if weak:
        return ProductSignature(
            dedupe_key=weak,
            family_key=family_key_from_product(product),
            variant=variant,
            match_tier="weak_id",
        )

    key = _text_strict_key(product, variant)
    return ProductSignature(
        dedupe_key=key,
        family_key=family_key_from_product(product),
        variant=variant,
        match_tier="text",
    )


def match_key(product: Product) -> str:
    """Pre-fuzzy strict key; deduplicator replaces text keys via fuzzy_match.assign_text_fuzzy_keys."""
    return build_signature(product).dedupe_key


def _score_title_quality(name: str) -> tuple[int, int]:
    n = normalize_text(name)
    score = 0
    if re.search(r"\b\d+gb\b|\b\d+tb\b", n):
        score += 3
    if re.search(r"\b\d+(?:\.\d+)?inch\b", n):
        score += 2
    if re.search(r"\b(19|20|21)\d{2}\b", n):
        score += 2
    if re.search(r"\b(pro|max|plus|ultra)\b", n):
        score += 1
    if re.search(
        r"\b(black|white|blue|red|green|gold|silver|gray|grey|graphite|titanium|starlight|midnight)\b",
        n,
    ):
        score += 1
    return score, len(name.strip())


def _storage_display(storage: str) -> str:
    if storage.endswith("gb"):
        return f"{storage[:-2]} GB"
    if storage.endswith("tb"):
        return f"{storage[:-2]} TB"
    return storage


def representative_name(products: list[Product], variant: VariantAttributes) -> str:
    """
    Pick one raw listing as the headline and append missing variant facts in parentheses.

    Deterministic: ``max`` by ``_score_title_quality``; ties break on title length, then first
    listing in iteration order. ``deduplicator`` passes clusters sorted by ``product.id``.
    """
    if not products:
        return ""

    best = max(products, key=lambda p: _score_title_quality(p.name))
    base = " ".join(best.name.split())
    base_n = normalize_text(base)

    parts: list[str] = []
    if variant.storage and not re.search(r"\b\d+gb\b|\b\d+tb\b", base_n):
        parts.append(_storage_display(variant.storage))
    if variant.size and not re.search(r"\b\d+(?:\.\d+)?inch\b", base_n):
        parts.append(variant.size.replace("in", '"'))
    if variant.year and variant.year not in base and variant.year not in base_n:
        parts.append(variant.year)
    if variant.editions:
        for ed in variant.editions:
            if ed not in base_n:
                parts.append(ed.upper())
    if variant.color:
        color_pretty = variant.color.replace("_", " ").title()
        if variant.color.replace("_", " ") not in base_n:
            parts.append(color_pretty)

    if not parts:
        return base

    return f"{base} ({', '.join(parts)})"
