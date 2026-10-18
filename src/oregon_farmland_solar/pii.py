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
    "phone": re.compile(r"(?<!\d)(?:\+?1[ .-]?)?(?:\(\d{3}\)|\d{3})[ .-]?\d{3}[ .-]?\d{4}(?!\d)"),
    "ssn": re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"),
}


@dataclass(frozen=True)
class Finding:
    kind: str
    match: str
    record_id: str | None = None


def scan_text(text: str, blocklist: Iterable[str] = ()) -> list[Finding]:
    findings = [
        Finding(kind, m.group()) for kind, rx in _PATTERNS.items() for m in rx.finditer(text)
    ]
    lowered = text.casefold()
    for term in blocklist:
        if term.strip() and term.casefold() in lowered:
            findings.append(Finding("blocklist", term))
    return findings


def scan_dataset(ds: Dataset, blocklist: Iterable[str] = ()) -> list[Finding]:
    blocklist = list(blocklist)
    out: list[Finding] = []
    for r in ds.reasons:
        for text in (r.quote, r.note or ""):
            for f in scan_text(text, blocklist):
                out.append(Finding(f.kind, f.match, record_id=r.id))
    return out
