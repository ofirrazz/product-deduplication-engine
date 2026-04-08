"""Example catalog rows for demos and tests."""

from __future__ import annotations

from models import Product


def sample_products() -> list[Product]:
    """
    Intentionally messy duplicates: mixed case, spacing, Hebrew/English, word order.

    After normalization + token matching, Samsung S23 and iPhone 15 Pro families collapse.
    """
    return [
        # Samsung Galaxy S23 family (English + Hebrew + spacing + order)
        Product("p1", "Samsung Galaxy S23", 2899.0, source="store_a"),
        Product("p2", "  samsung   galaxy s23", 2750.0, source="store_b"),
        Product("p3", "סמסונג גלקסי S23", 2999.0, source="store_c"),
        Product("p4", "S23 Samsung Galaxy", 2800.0, source="store_d"),
        Product("p5", "23S Samsung", 2700.0, source="store_e"),
        # iPhone 15 Pro family
        Product("p6", "iPhone 15 Pro", 4299.0, source="store_a"),
        Product("p7", "IPHONE 15 PRO 256GB", 4199.0, source="store_b"),
        Product("p8", "אייפון 15 פרו", 4399.0, source="store_c"),
        Product("p9", "Pro 15 iPhone", 4100.0, source="store_d"),
        # Distinct product (should stay separate)
        Product("p10", "Samsung Galaxy S24", 3200.0, source="store_a"),
    ]
