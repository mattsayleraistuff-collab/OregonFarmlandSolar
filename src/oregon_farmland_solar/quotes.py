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
    """Result of looking for a quote on a page.

    Attributes:
        found: True if the quote was located.
        exact: True for an exact match after normalizing; False for a fuzzy match, which a
            person should review.
        score: 100 for an exact match, the fuzzy score for a fuzzy one, 0 if not found.
    """

    found: bool
    exact: bool
    score: float


def _squash(text: str, *, strip_line_numbers: bool) -> str:
    """Reduces text to lowercase letters and digits so formatting differences do not matter."""
    text = unicodedata.normalize("NFKC", text).replace("­", "")
    if strip_line_numbers:
        text = re.sub(r"(?m)^[ \t]*\d{1,3}(?=[ \t])", "", text)  # margin line numbers
    text = re.sub(r"-[ \t]*\n[ \t]*", "", text)  # re-join hyphenated line breaks
    return re.sub(r"[^a-z0-9]", "", text.casefold())


def check_quote(quote: str, page_text: str) -> QuoteCheck:
    """Looks for a quote in the text of one page.

    Both sides are normalized (case, punctuation, whitespace, margin line numbers and
    hyphenated line breaks are ignored). If there is no exact match and the quote has at
    least ``MIN_FUZZY_CHARS`` characters, a fuzzy match at or above ``FUZZY_THRESHOLD``
    counts, to tolerate OCR noise.

    Args:
        quote: The quote as coded.
        page_text: Extracted text of the cited page.

    Returns:
        A QuoteCheck; empty inputs are never found.
    """
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
