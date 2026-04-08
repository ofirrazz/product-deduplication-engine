"""Text normalization for product names (rule-based; extendable)."""

from __future__ import annotations

import re
import unicodedata

# Hebrew → English glosses for common mobile brand/model words.
# Extend this dict as you onboard more categories or locales.
_HEBREW_TO_ENGLISH: dict[str, str] = {
    "סמסונג": "samsung",
    "גלקסי": "galaxy",
    "אייפון": "iphone",
    "פרו": "pro",
    "מקס": "max",
    "אולטרה": "ultra",
    "פלוס": "plus",
}

_MULTI_SPACE = re.compile(r"\s+")
_NON_ALNUM_SPACE = re.compile(r"[^\w\s\-]", re.UNICODE)


def _collapse_samsung_s_line(s: str) -> str:
    """Fold common Samsung + Galaxy + S-model permutations to 'samsung sNN'."""
    s = re.sub(r"\bsamsung\s+galaxy\s+(s\d+)\b", r"samsung \1", s)
    s = re.sub(r"\b(s\d+)\s+samsung\s+galaxy\b", r"samsung \1", s)
    s = re.sub(r"\bgalaxy\s+(s\d+)\s+samsung\b", r"samsung \1", s)
    s = re.sub(r"\b(s\d+)\s+samsung\b", r"samsung \1", s)
    return s


def normalize_text(name: str) -> str:
    """
    Apply rule-based normalization: case, spacing, Hebrew glosses, light punctuation cleanup.

    Future: plug in ML transliteration, brand dictionaries from a CMS, or NER-based cleanup.
    """
    if not name:
        return ""

    s = unicodedata.normalize("NFKC", name)
    s = s.strip().lower()

    for he, en in _HEBREW_TO_ENGLISH.items():
        s = s.replace(he.lower(), en)

    s = _collapse_samsung_s_line(s)

    # Strip storage sizes so "iPhone 15 Pro" and "iPhone 15 Pro 256GB" share a key.
    # Future: keep SKU-level splits when prices differ by storage; use attributes, not name-only.
    s = re.sub(r"\b\d+\s*gb\b", "", s, flags=re.IGNORECASE)

    s = _NON_ALNUM_SPACE.sub(" ", s)
    s = _MULTI_SPACE.sub(" ", s)
    return s.strip()
