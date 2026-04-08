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

    def __post_init__(self) -> None:
        if self.price < 0:
            raise ValueError("price must be non-negative")


@dataclass
class UnifiedProduct:
    """One logical product after deduplication: best display name and lowest seen price."""

    canonical_name: str
    min_price: float
    currency: str
    product_ids: tuple[str, ...] = field(default_factory=tuple)
    raw_names: tuple[str, ...] = field(default_factory=tuple)
