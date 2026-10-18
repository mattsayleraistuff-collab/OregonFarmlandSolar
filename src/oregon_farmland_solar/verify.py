"""Verify coded quotes against the local source PDFs (which are never published)."""

from __future__ import annotations

import hashlib
import subprocess
from collections.abc import Callable
from pathlib import Path

from .dataset import Dataset, Issue
from .quotes import check_quote


def extract_pages(pdf: Path) -> list[str]:
    """Per-page text via poppler's pdftotext (pages are separated by form feeds)."""
    out = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"], check=True, capture_output=True, text=True
    ).stdout
    pages = out.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return pages


def index_pdfs(
    pdf_dir: Path, extract: Callable[[Path], list[str]] = extract_pages
) -> dict[str, list[str]]:
    """Map sha256 of each PDF under pdf_dir to its per-page text."""
    return {
        hashlib.sha256(p.read_bytes()).hexdigest(): extract(p)
        for p in sorted(Path(pdf_dir).rglob("*.pdf"))
    }


def verify_quotes(ds: Dataset, pdfs: dict[str, list[str]]) -> list[Issue]:
    """Check each real reason's quote appears on its cited page of the matching PDF."""
    issues: list[Issue] = []
    docs = {d.id: d for d in ds.documents}
    reported: set[str] = set()
    for r in ds.reasons:
        doc = docs.get(r.document_id)
        if r.synthetic or doc is None or doc.sha256 is None:
            continue
        pages = pdfs.get(doc.sha256)
        if pages is None:
            if doc.id not in reported:
                reported.add(doc.id)
                issues.append(
                    Issue(
                        "warning", f"document {doc.id!r}: no local PDF with that sha256; unverified"
                    )
                )
            continue
        if doc.id not in reported:
            reported.add(doc.id)
            if doc.page_count is not None and doc.page_count != len(pages):
                issues.append(
                    Issue(
                        "error", f"document {doc.id!r}: page_count {doc.page_count} != {len(pages)}"
                    )
                )
        if not 1 <= r.pdf_page <= len(pages):
            issues.append(Issue("error", f"reason {r.id!r}: pdf_page {r.pdf_page} out of range"))
            continue
        result = check_quote(r.quote, pages[r.pdf_page - 1])
        if not result.found:
            issues.append(
                Issue("error", f"reason {r.id!r}: quote not found on pdf_page {r.pdf_page}")
            )
        elif not result.exact:
            issues.append(
                Issue("warning", f"reason {r.id!r}: fuzzy quote match ({result.score:.0f}); check")
            )
    return issues
