"""Example catalog rows for demos and tests."""

from __future__ import annotations

from models import Product


def sample_products() -> list[Product]:
    """
    Cross-category examples: identifiers, weak SKUs, and text+fuzzy rows.

    Includes pairs that should merge vs pairs that must stay separate (size/storage/year).
    """
    return [
        # --- Strong barcode (GTIN field holds EAN-13 style data) ---
        Product(
            "g1",
            "Apple iPhone 15 Pro 256GB - Black",
            4399.0,
            gtin="01959490668208",
            brand="Apple",
            source="store_alpha",
        ),
        Product(
            "g2",
            "אייפון 15 פרו 256 גיגה",
            4299.0,
            ean="01959490668208",
            brand="Apple",
            source="store_beta",
        ),
        Product(
            "g3",
            "iPhone 15 Pro 256GB (open box)",
            4250.0,
            gtin="01959490668208",
            brand="Apple",
            gtin_trusted=False,
            source="store_gamma",
        ),
        # --- Strong MPN + brand ---
        Product(
            "m1",
            "Sony Headphones WH-1000XM5 Black",
            1299.0,
            mpn="WH-1000XM5/B",
            brand="Sony",
            source="audio_a",
        ),
        Product(
            "m2",
            "WH1000XM5 wireless NC headphones",
            1249.0,
            mpn="wh1000xm5/b",
            brand="Sony",
            source="audio_b",
        ),
        # --- Weak SKU ---
        Product(
            "w1",
            "Galaxy Tab S9 128GB Wifi",
            1899.0,
            sku="  TAB-S9-128  ",
            brand="Samsung",
            source="same_retailer",
        ),
        Product(
            "w2",
            "Samsung TAB S9 128gb wifi",
            1850.0,
            sku="tab-s9-128",
            brand="Samsung",
            source="same_retailer",
        ),
        # --- TV: text + fuzzy (similar titles, same size/year) ---
        Product(
            "tv1",
            'LG OLED 55" 4K Smart TV 2023',
            4999.0,
            brand="LG",
            source="tv_shop_a",
        ),
        Product(
            "tv2",
            "LG OLED 55 inch 4k smart טלוויזיה 2023",
            4899.0,
            brand="LG",
            source="tv_shop_b",
        ),
        # Different diagonal -> must not merge with tv1/tv2
        Product(
            "tv3",
            "LG OLED 65 inch 4K 2023",
            6200.0,
            brand="LG",
            source="tv_shop_c",
        ),
        # --- Laptop: text + fuzzy ---
        Product(
            "lp1",
            "Lenovo ThinkPad X1 Carbon 512 GB 14 inch",
            7299.0,
            brand="Lenovo",
            source="pc_world",
        ),
        Product(
            "lp2",
            "Thinkpad X1 Carbon 512gb 14inch laptop",
            6999.0,
            brand="Lenovo",
            source="pc_online",
        ),
        # Different storage -> separate
        Product(
            "lp3",
            "Lenovo ThinkPad X1 Carbon 256gb 14 inch",
            6599.0,
            brand="Lenovo",
            source="pc_world",
        ),
        # --- Appliance: typo / spelling noise (fuzzy) ---
        Product(
            "ap1",
            "Whirlpool Dishwasher WDT730PAHZ stainless",
            2499.0,
            brand="Whirlpool",
            source="appliance_a",
        ),
        Product(
            "ap2",
            "Whirpool Dishwasher WDT730PAHZ - stainless steel",
            2399.0,
            brand="Whirlpool",
            source="appliance_b",
        ),
        # --- Phones: text + fuzzy + separation by variant ---
        # Inverted model token + EN/HE (normalizer folds to same family fingerprint).
        Product("ph0", "23S Samsung", 2850.0, source="market_a"),
        Product("ph1", "Samsung Galaxy S23", 2899.0, source="market_a"),
        Product("ph2", "  samsung   galaxy s23", 2750.0, source="market_b"),
        Product("ph3", "סמסונג גלקסי S23", 2999.0, source="market_c"),
        Product("ph4", "Samsung Galaxy S23 128GB", 2600.0, source="market_d"),
        Product("ph5", "Galaxy S23 256 gb", 2700.0, source="market_e"),
        Product("ph6", "Samsung Galaxy S24", 3200.0, source="market_f"),
        Product("ph7", "iPhone 15 Pro 128GB", 3999.0, source="market_g"),
        Product("ph8", "IPHONE 15 PRO 256GB", 4199.0, source="market_h"),
        Product("ph9", "iPhone 15 Pro Max 256GB", 4799.0, source="market_i"),
        Product(
            "ph10",
            "iPhone 15 Pro 256GB Black 2024",
            4299.0,
            source="market_j",
        ),
        Product(
            "ph11",
            "אייפון 15 פרו 256 גיגה לבן 2024",
            4199.0,
            source="market_k",
        ),
        Product(
            "ph12",
            "iPhone 15 Pro Max 256GB White",
            4699.0,
            source="market_l",
        ),
        # --- Fuzzy edge cases (text tier) ---
        # Typo / spelling noise -> should merge (same variant bucket, high token_sort_ratio).
        Product(
            "edge_typo_a",
            "Jabra Elite 85t True Wireless earbuds charcoal",
            599.0,
            brand="Jabra",
            source="edge_audio",
        ),
        Product(
            "edge_typo_b",
            "Jabra Elite 85t True Wirless earbuds charcoal",
            579.0,
            brand="Jabra",
            source="edge_audio",
        ),
        # Same family line but different model tokens -> should NOT merge under default fuzzy threshold.
        Product(
            "edge_near_a",
            "Bose SoundLink Flex Bluetooth speaker Black",
            899.0,
            brand="Bose",
            source="edge_audio",
        ),
        Product(
            "edge_near_b",
            "Bose SoundLink Micro Bluetooth speaker Black",
            849.0,
            brand="Bose",
            source="edge_audio",
        ),
        # Different finishes -> different color in variant key -> separate buckets (no fuzzy across).
        Product(
            "edge_color_a",
            "Google Pixel 8 128GB Obsidian",
            3299.0,
            brand="Google",
            source="edge_pixel",
        ),
        Product(
            "edge_color_b",
            "Google Pixel 8 128GB Porcelain",
            3199.0,
            brand="Google",
            source="edge_pixel",
        ),
        # Explicit storage vs missing storage -> different variant keys -> never merge.
        Product(
            "edge_ssd_a",
            "Samsung Portable SSD T7 1tb gray",
            449.0,
            brand="Samsung",
            source="edge_storage",
        ),
        Product(
            "edge_ssd_b",
            "Samsung Portable SSD T7 gray",
            459.0,
            brand="Samsung",
            source="edge_storage",
        ),
    ]
