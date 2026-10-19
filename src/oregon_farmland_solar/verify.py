"""Verify coded quotes against the local source PDFs (which are never published)."""

from __future__ import annotations

import hashlib
import subprocess
from collections.abc import Callable
from pathlib import Path

from .dataset import Dataset, Issue
from .quotes import check_quote


def extract_pages(pdf: Path) -> list[str]:
    """Extracts per-page text with poppler's ``pdftotext``.

    Args:
        pdf: Path to the PDF file.

    Returns:
        One string per page, in order. Layout is preserved so margin line numbers stay on
        their own lines (``check_quote`` strips them).

    Raises:
        FileNotFoundError: If ``pdftotext`` is not installed.
        subprocess.CalledProcessError: If ``pdftotext`` fails on the file.
    """
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
    """Reads every PDF under a folder and indexes its text by checksum.

    Args:
        pdf_dir: Folder searched recursively for ``*.pdf`` files.
        extract: Function returning per-page text for one PDF. Replaceable so tests do not
            need poppler.

    Returns:
        Mapping of each file's SHA-256 (lowercase hex) to its list of page texts.
    """
    return {
        hashlib.sha256(p.read_bytes()).hexdigest(): extract(p)
        for p in sorted(Path(pdf_dir).rglob("*.pdf"))
    }


def verify_quotes(ds: Dataset, pdfs: dict[str, list[str]]) -> list[Issue]:
    """Checks that each real reason's quote appears on its cited page.

    Synthetic reasons are skipped. A document whose PDF is not in ``pdfs`` produces one
    warning (it may simply not be on this machine); a quote that is missing, or a page
    number out of range, is an error; a fuzzy (non-exact) match is a warning.

    Args:
        ds: Dataset to check.
        pdfs: Page texts keyed by SHA-256, as returned by ``index_pdfs``.

    Returns:
        Issues found, possibly empty.
    """
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
                where = f" (expected file {doc.file_name!r})" if doc.file_name else ""
                issues.append(
                    Issue(
                        "warning",
                        f"document {doc.id!r}: no local PDF with that sha256{where}; unverified",
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
