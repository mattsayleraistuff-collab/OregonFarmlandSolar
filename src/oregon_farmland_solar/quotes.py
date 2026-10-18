"""Check that a coded quote really appears on its cited page.

Page text from PDFs is messy: line numbers in the margin, hyphenated line breaks, curly
quotes and OCR noise. Both sides are reduced to lowercase letters and digits before
comparing, with a fuzzy fallback for longer quotes. A quote that fails this check should be
treated as unverified (it may be a misquote or a model hallucination).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz

FUZZY_THRESHOLD = 90.0  # fuzzy hits have exact=False so a person can review them
MIN_FUZZY_CHARS = 25


@dataclass(frozen=True)
class QuoteCheck:
    found: bool
    exact: bool
    score: float


def _squash(text: str, *, strip_line_numbers: bool) -> str:
    text = unicodedata.normalize("NFKC", text).replace("­", "")
    if strip_line_numbers:
        text = re.sub(r"(?m)^[ \t]*\d{1,3}(?=[ \t])", "", text)  # margin line numbers
    text = re.sub(r"-[ \t]*\n[ \t]*", "", text)  # re-join hyphenated line breaks
    return re.sub(r"[^a-z0-9]", "", text.casefold())


def check_quote(quote: str, page_text: str) -> QuoteCheck:
    q = _squash(quote, strip_line_numbers=False)
    p = _squash(page_text, strip_line_numbers=True)
    if not q or not p:
        return QuoteCheck(False, False, 0.0)
    if q in p:
        return QuoteCheck(True, True, 100.0)
    if len(q) < MIN_FUZZY_CHARS:
        return QuoteCheck(False, False, 0.0)
    score = float(fuzz.partial_ratio(q, p))
    return QuoteCheck(score >= FUZZY_THRESHOLD, False, score)
