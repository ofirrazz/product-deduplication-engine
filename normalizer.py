"""Generic text normalization and attribute extraction for product matching."""

from __future__ import annotations

import re
import unicodedata

from models import VariantAttributes

# Small Hebrew → English gloss for commerce (units, colors, editions, frequent Latin-script gaps).
# Not the primary matching strategy: identifiers + attributes + fuzzy similarity carry most weight.
_HEBREW_COMMERCE_GLOSSARY: dict[str, str] = {
    "סמסונג": "samsung",
    "גלקסי": "galaxy",
    "אייפון": "iphone",
    "פרו": "pro",
    "מקס": "max",
    "פלוס": "plus",
    "אולטרה": "ultra",
    "ג'יגה": "gb",
    "ג׳יגה": "gb",
    "גיגה": "gb",
    "טרה": "tb",
    "טרבייט": "tb",
    "אינץ": "inch",
    "טלוויזיה": "tv",
    "מחשב": "laptop",
    "שחור": "black",
    "לבן": "white",
    "כחול": "blue",
    "אדום": "red",
    "ירוק": "green",
    "סגול": "purple",
    "זהב": "gold",
    "כסף": "silver",
    "אפור": "gray",
}

_EDITION_ORDER: tuple[str, ...] = ("pro", "max", "plus", "ultra")

_MULTI_SPACE = re.compile(r"\s+")
# Keep word chars, dots (decimals), hyphens (SKU-like tokens); turn other punctuation to spaces.
_NON_ALNUM_SPACE = re.compile(r"[^\w\s\.\-]", re.UNICODE)

_STORAGE_GB_RE = re.compile(r"\b(\d+)\s*gb\b", re.IGNORECASE)
_STORAGE_TB_RE = re.compile(r"\b(\d+)\s*tb\b", re.IGNORECASE)
_STORAGE_TOKEN_RE = re.compile(r"\b\d+gb\b|\b\d+tb\b", re.IGNORECASE)

_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2}|21\d{2})\b")

_SIZE_RE = re.compile(r"\b(\d{1,3}(?:\.\d{1,2})?)inch\b", re.IGNORECASE)
_SIZE_TOKEN_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,2})?inch\b", re.IGNORECASE)

_EDITION_TOKEN_RE = re.compile(r"\b(?:pro|max|plus|ultra)\b", re.IGNORECASE)

_COLOR_TERMS: tuple[str, ...] = (
    "space gray",
    "space grey",
    "rose gold",
    "midnight blue",
    "product red",
    "phantom black",
    "titanium black",
    "titanium white",
    "titanium natural",
    "graphite",
    "starlight",
    "midnight",
    "lavender",
    "sierra blue",
    "deep purple",
    "obsidian",
    "porcelain",
    "bay",
    "coral",
    "black",
    "white",
    "silver",
    "gold",
    "blue",
    "red",
    "green",
    "purple",
    "orange",
    "yellow",
    "pink",
    "brown",
    "gray",
    "grey",
    "bronze",
    "titanium",
)


def _color_term_pattern(term: str) -> str:
    parts = term.split()
    return r"\b" + r"\s+".join(re.escape(p) for p in parts) + r"\b"


_COLOR_PATTERN = re.compile(
    "(" + "|".join(_color_term_pattern(t) for t in sorted(_COLOR_TERMS, key=len, reverse=True)) + ")",
    re.IGNORECASE,
)


def unicode_normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def lowercase(text: str) -> str:
    return text.lower()


def collapse_whitespace(text: str) -> str:
    return _MULTI_SPACE.sub(" ", text).strip()


def strip_punctuation_to_spaces(text: str) -> str:
    return _NON_ALNUM_SPACE.sub(" ", text)


def normalize_quotes_and_inch_marks(text: str) -> str:
    """Map double-quote inch marks to a spoken inch token (avoid treating ' as inches)."""
    s = text.replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace('"', " inch ")
    return s


def compact_number_unit_patterns(text: str) -> str:
    """
    Normalize human spacing between numbers and units into single tokens.

    Examples after full pipeline intent:
    - 256 gb / 256 GB -> 256gb
    - 1 tb -> 1tb
    - 55 inch -> 55inch (after quote normalization)
    - 15.6 inch -> 15.6inch
    """
    s = text
    s = re.sub(r"\b(\d+(?:\.\d+)?)\s+gb\b", r"\1gb", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(\d+(?:\.\d+)?)\s+tb\b", r"\1tb", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(\d+(?:\.\d+)?)\s+inch\b", r"\1inch", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(\d+(?:\.\d+)?)\s+in\b", r"\1inch", s, flags=re.IGNORECASE)
    return s


def split_glued_edition_suffixes(text: str) -> str:
    """Generic: 15pro / 13max -> split trailing edition tokens from digits."""
    return re.sub(r"(\d)(pro|max|plus|ultra)\b", r"\1 \2", text, flags=re.IGNORECASE)


def apply_hebrew_commerce_glossary(text: str) -> str:
    s = text
    for he, en in _HEBREW_COMMERCE_GLOSSARY.items():
        s = s.replace(he, en)
    return s


# Tiny typo normalizations (keep small; prefer supplier data fixes in production).
_COMMON_TOKEN_FIXES: tuple[tuple[str, str], ...] = (
    ("whirpool", "whirlpool"),
)


def apply_common_token_fixes(text: str) -> str:
    s = text
    for bad, good in _COMMON_TOKEN_FIXES:
        s = re.sub(rf"\b{re.escape(bad)}\b", good, s)
    s = re.sub(r"\bstainless\s+steel\b", "stainless", s)
    return s


def _has_samsung_galaxy_context(text: str) -> bool:
    """True when the title plausibly refers to Samsung Galaxy copy (brand token or standalone Galaxy line)."""
    return "samsung" in text or "galaxy" in text


def normalize_inverted_nn_s_suffix(text: str) -> str:
    """
    Map ``NNs`` → ``sNN`` for two-digit tokens (e.g. ``23s`` → ``s23``).

    **Targeted rule, not a synonym dictionary:** addresses a high-volume retail typo pattern
    for Galaxy **S**-series style listings. Restricted to ``[12]\\d`` to limit false positives.
    In production, add similar small regexes only when metrics justify them.
    """
    return re.sub(r"\b([12]\d)s\b", r"s\1", text, flags=re.IGNORECASE)


def normalize_samsung_galaxy_s_series(text: str) -> str:
    """
    Collapse a few ``samsung`` / ``galaxy`` / ``s<number>`` word orders to ``samsung s<number>``.

    Same human intent as “Samsung Galaxy S23” / “Galaxy S23” / “23S Samsung” (internal form is
    lowercased for matching). **Regex-only, no per-SKU list.** Scoped to this naming pattern so
    the rest of the pipeline stays category-agnostic.
    """
    s = text
    s = re.sub(r"\bsamsung\s+galaxy\s+(s\d+)\b", r"samsung \1", s)
    s = re.sub(r"\b(s\d+)\s+samsung\s+galaxy\b", r"samsung \1", s)
    s = re.sub(r"\bgalaxy\s+(s\d+)\s+samsung\b", r"samsung \1", s)
    s = re.sub(r"\b(s\d+)\s+samsung\b", r"samsung \1", s)
    return s


def normalize_samsung_s_line_titles(text: str) -> str:
    """
    Apply inverted-``NNs`` and Galaxy **S**-line word-order normalization **only** in Samsung/Galaxy context.

    Skips unrelated titles so ``23s`` in other domains is not rewritten. This block is the
    deliberate “small OEM-shaped exception”: minimal surface area, data-driven if extended.
    """
    if not _has_samsung_galaxy_context(text):
        return text
    s = normalize_inverted_nn_s_suffix(text)
    s = normalize_samsung_galaxy_s_series(s)
    return s


def normalize_text(name: str) -> str:
    """
    Compose generic, reusable normalization steps (deterministic).

    Order matters: quotes/inches expand, units compact, Hebrew gloss, then guarded Galaxy S-line regex
    (only if ``samsung``/``galaxy`` appear), then tiny token fixes, then punctuation stripping.
    """
    if not name:
        return ""

    s = unicode_normalize(name)
    s = lowercase(s)
    s = collapse_whitespace(s)
    s = normalize_quotes_and_inch_marks(s)
    s = collapse_whitespace(s)
    s = compact_number_unit_patterns(s)
    s = split_glued_edition_suffixes(s)
    s = apply_hebrew_commerce_glossary(s)
    s = normalize_samsung_s_line_titles(s)
    s = apply_common_token_fixes(s)
    s = strip_punctuation_to_spaces(s)
    s = collapse_whitespace(s)
    return s


def extract_storage(normalized: str) -> str | None:
    match_gb = _STORAGE_GB_RE.search(normalized)
    if match_gb:
        return f"{match_gb.group(1)}gb"
    match_tb = _STORAGE_TB_RE.search(normalized)
    if match_tb:
        return f"{match_tb.group(1)}tb"
    return None


def extract_year(normalized: str) -> str | None:
    match = _YEAR_RE.search(normalized)
    return match.group(1) if match else None


def _format_size_token(raw: str) -> str:
    value = raw.rstrip("0").rstrip(".") if "." in raw else raw
    return f"{value}in"


def extract_size(normalized: str) -> str | None:
    match = _SIZE_RE.search(normalized)
    if not match:
        return None
    return _format_size_token(match.group(1))


def extract_editions(normalized: str) -> tuple[str, ...]:
    tokens = set(_EDITION_TOKEN_RE.findall(normalized))
    return tuple(token for token in _EDITION_ORDER if token in tokens)


def extract_color(normalized: str) -> str | None:
    match = _COLOR_PATTERN.search(normalized)
    if not match:
        return None
    return match.group(1).lower().replace(" ", "_")


def extract_variant_attributes(name: str) -> VariantAttributes:
    normalized = normalize_text(name)
    return VariantAttributes(
        storage=extract_storage(normalized),
        year=extract_year(normalized),
        size=extract_size(normalized),
        color=extract_color(normalized),
        editions=extract_editions(normalized),
    )


def remove_variant_tokens(normalized: str) -> str:
    family = _STORAGE_TOKEN_RE.sub(" ", normalized)
    family = _YEAR_RE.sub(" ", family)
    family = _SIZE_TOKEN_RE.sub(" ", family)
    family = _EDITION_TOKEN_RE.sub(" ", family)
    family = _COLOR_PATTERN.sub(" ", family)
    family = _MULTI_SPACE.sub(" ", family)
    return family.strip()
