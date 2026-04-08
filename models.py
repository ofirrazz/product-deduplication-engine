"""Domain models for product deduplication."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Product:
    """A single offer for a product (may duplicate other offers under a different name)."""

    id: str
    name: str
    price: float
    currency: str = "ILS"
    source: Optional[str] = None
    sku: Optional[str] = None
    # Any of GTIN / EAN / UPC may be populated; normalization collapses to digits (see matcher).
    gtin: Optional[str] = None
    ean: Optional[str] = None
    upc: Optional[str] = None
    mpn: Optional[str] = None
    brand: Optional[str] = None
    gtin_trusted: bool = True
    mpn_trusted: bool = True

    def __post_init__(self) -> None:
        if self.price < 0:
            raise ValueError("price must be non-negative")


@dataclass(frozen=True)
class VariantAttributes:
    """Variant-level facts extracted from the title (conservative deduplication)."""

    storage: Optional[str] = None
    year: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    editions: tuple[str, ...] = ()

    @property
    def key(self) -> str:
        edition_part = ",".join(self.editions) if self.editions else "unknown"
        return (
            f"storage={self.storage or 'unknown'}"
            f"|year={self.year or 'unknown'}"
            f"|size={self.size or 'unknown'}"
            f"|color={self.color or 'unknown'}"
            f"|edition={edition_part}"
        )

    @property
    def key_for_strong_catalog_id(self) -> str:
        edition_part = ",".join(self.editions) if self.editions else "unknown"
        return (
            f"storage={self.storage or 'unknown'}"
            f"|year={self.year or 'unknown'}"
            f"|size={self.size or 'unknown'}"
            f"|edition={edition_part}"
        )


@dataclass(frozen=True)
class ProductSignature:
    """Parsed identity: how we grouped this listing."""

    dedupe_key: str
    family_key: str
    variant: VariantAttributes
    match_tier: str  # "strong_id" | "weak_id" | "text" | "text_fuzzy"


@dataclass
class UnifiedProduct:
    """One logical product after deduplication: canonical name and lowest seen price."""

    canonical_name: str
    min_price: float
    currency: str
    dedupe_key: str = ""
    match_tier: str = ""
    family_key: str = ""
    variant_key: str = ""
    product_ids: tuple[str, ...] = field(default_factory=tuple)
    raw_names: tuple[str, ...] = field(default_factory=tuple)
