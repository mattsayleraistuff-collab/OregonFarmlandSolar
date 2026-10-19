"""Heuristic scan for personal information in text destined for the public repo.

This only finds candidates (emails, US phone numbers, SSN-shaped numbers, and any terms in a
caller-supplied blocklist). It does not prove text is clean: a person still reviews quotes.
Keep real blocklists out of the repo (for example in a git-ignored local file).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from .dataset import Dataset

_PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    # Not followed by "(" and not preceded by "OAR": Oregon rule numbers such as
    # "OAR 660-033-0130(38)" have the same shape as a phone number.
    "phone": re.compile(
        r"(?<!OAR )(?<!\d)(?:\+?1[ .-]?)?(?:\(\d{3}\)|\d{3})[ .-]?\d{3}[ .-]?\d{4}(?![\d(])"
    ),
    "ssn": re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"),
}


@dataclass(frozen=True)
class Finding:
    """A possible piece of personal information.

    Attributes:
        kind: "email", "phone", "ssn" or "blocklist".
        match: The text that matched.
        record_id: Id of the reason it was found in, when scanning a dataset.
    """

    kind: str
    match: str
    record_id: str | None = None


def scan_text(text: str, blocklist: Iterable[str] = ()) -> list[Finding]:
    """Scans one string for candidate personal information.

    Args:
        text: Text to scan.
        blocklist: Names or terms to flag, matched case-insensitively.

    Returns:
        One Finding per match, possibly empty.
    """
    findings = [
        Finding(kind, m.group()) for kind, rx in _PATTERNS.items() for m in rx.finditer(text)
    ]
    lowered = text.casefold()
    for term in blocklist:
        if term.strip() and term.casefold() in lowered:
            findings.append(Finding("blocklist", term))
    return findings


def scan_dataset(ds: Dataset, blocklist: Iterable[str] = ()) -> list[Finding]:
    """Scans the quote and note of every reason in a dataset.

    Args:
        ds: Dataset to scan.
        blocklist: Names or terms to flag, matched case-insensitively.

    Returns:
        Findings with ``record_id`` set to the reason they came from.
    """
    blocklist = list(blocklist)
    out: list[Finding] = []
    for r in ds.reasons:
        for text in (r.quote, r.note or ""):
            for f in scan_text(text, blocklist):
                out.append(Finding(f.kind, f.match, record_id=r.id))
    return out
