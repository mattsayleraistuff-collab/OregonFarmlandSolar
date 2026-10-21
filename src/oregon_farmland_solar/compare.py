"""Compare machine-proposed reasons with the hand-coded ones for the same document.

The comparison is a measuring tool, not a verdict. Hand-coded reasons are a deliberate,
selective set (one quote per distinct reason), while the model proposes every candidate it
finds, so extras are expected and need a person's judgment.
"""

from __future__ import annotations

import difflib
import hashlib
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SAME = 0.9
PARTIAL = 0.5
SAME_LENGTH = 0.8

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})


def normalize(text: str) -> list[str]:
    """Lower-cases text, straightens curly quotes and splits it into words."""
    return re.sub(r"\s+", " ", text.translate(_QUOTES)).strip().lower().split()


def overlap(a: Sequence[str], b: Sequence[str]) -> float:
    """Share of the shorter word list that appears in order in the other (0 to 1)."""
    if not a or not b:
        return 0.0
    blocks = difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks()
    return sum(m.size for m in blocks) / min(len(a), len(b))


@dataclass(frozen=True)
class Match:
    """A hand-coded reason and the proposed quote that covers it."""

    hand: dict[str, Any]
    found: dict[str, Any]
    score: float
    kind: str  # "same" or "partial"


@dataclass(frozen=True)
class Missed:
    """A hand-coded reason on a scanned page that nothing proposed matched."""

    hand: dict[str, Any]
    why: str

    @property
    def id(self) -> str:
        """The hand-coded reason's id."""
        return str(self.hand["id"])


@dataclass(frozen=True)
class Extra:
    """A proposed quote that matches no hand-coded reason."""

    found: dict[str, Any]
    page_has_hand_coded: bool


@dataclass
class Comparison:
    """The result of comparing one document."""

    matches: list[Match] = field(default_factory=list)
    missed: list[Missed] = field(default_factory=list)
    not_scanned: list[dict[str, Any]] = field(default_factory=list)
    extras: list[Extra] = field(default_factory=list)
    scanned_pages: list[int] = field(default_factory=list)

    @property
    def recall(self) -> float | None:
        """Share of hand-coded reasons (on scanned pages) that were matched."""
        total = len(self.matches) + len(self.missed)
        return len(self.matches) / total if total else None


def _why_missed(hand: dict[str, Any], held: Iterable[dict[str, Any]]) -> str:
    words = normalize(hand["quote"])
    for h in held:
        if h["pdf_page"] == hand["pdf_page"] and overlap(words, normalize(h["quote"])) >= PARTIAL:
            detail = f" ({h['reason']})" if h.get("reason") else ""
            if h.get("status") == "review":
                return "held for review" + detail
            return "rejected by the quote check" + detail
    return "not proposed"


def _kind(score: float, hand: dict[str, Any], found: dict[str, Any]) -> str:
    """Returns "same" for near-identical words and length, otherwise "partial"."""
    a, b = len(normalize(hand["quote"])), len(normalize(found["quote"]))
    close = min(a, b) / max(a, b) >= SAME_LENGTH if a and b else False
    return "same" if score >= SAME and close else "partial"


def compare(
    hand_coded: Sequence[dict[str, Any]],
    proposed: Sequence[dict[str, Any]],
    *,
    scanned_pages: Iterable[int],
    held_back: Sequence[dict[str, Any]] = (),
) -> Comparison:
    """Matches proposed quotes to hand-coded ones page by page.

    Args:
        hand_coded: Hand-coded reasons (``id``, ``pdf_page``, ``quote``).
        proposed: Accepted machine candidates (``id``, ``pdf_page``, ``quote``).
        scanned_pages: Pages the model actually read.
        held_back: Quotes the quote check held for review or rejected (``status``, ``reason``).

    Returns:
        A Comparison. Each quote is used in at most one match, best score first.
    """
    scanned = sorted(set(scanned_pages))
    out = Comparison(scanned_pages=scanned)
    pairs = []
    for hi, h in enumerate(hand_coded):
        hw = normalize(h["quote"])
        for fi, f in enumerate(proposed):
            if h["pdf_page"] == f["pdf_page"]:
                s = overlap(hw, normalize(f["quote"]))
                if s >= PARTIAL:
                    pairs.append((s, hi, fi))
    used_h: set[int] = set()
    used_f: set[int] = set()
    for s, hi, fi in sorted(pairs, key=lambda t: (-t[0], t[1], t[2])):
        if hi in used_h or fi in used_f:
            continue
        used_h.add(hi)
        used_f.add(fi)
        out.matches.append(
            Match(hand_coded[hi], proposed[fi], round(s, 3), _kind(s, hand_coded[hi], proposed[fi]))
        )
    out.matches.sort(key=lambda m: (m.hand["pdf_page"], str(m.hand["id"])))
    for hi, h in enumerate(hand_coded):
        if hi in used_h:
            continue
        if h["pdf_page"] in scanned:
            out.missed.append(Missed(h, _why_missed(h, held_back)))
        else:
            out.not_scanned.append(h)
    hand_pages = {h["pdf_page"] for h in hand_coded}
    for fi, f in enumerate(proposed):
        if fi not in used_f:
            out.extras.append(Extra(f, f["pdf_page"] in hand_pages))
    return out


def manifest_path_for(candidates: Path, *, must_exist: bool = False) -> Path:
    """The run manifest that sits beside a candidates file."""
    path = candidates.with_name(candidates.name.replace(".candidates.json", ".manifest.json"))
    if must_exist and not path.exists():
        raise FileNotFoundError(f"No run manifest beside {candidates}: expected {path}")
    return path


def sha256_file(path: Path) -> str:
    """SHA-256 of a file, for the audit trail."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summary(c: Comparison, hand_total: int) -> dict[str, Any]:
    """Counts for the JSON summary."""
    return {
        "hand_coded": hand_total,
        "matched": len(c.matches),
        "matched_same": sum(m.kind == "same" for m in c.matches),
        "matched_partial": sum(m.kind == "partial" for m in c.matches),
        "missed": len(c.missed),
        "not_scanned": len(c.not_scanned),
        "extras": len(c.extras),
        "extras_on_pages_with_hand_coded": sum(e.page_has_hand_coded for e in c.extras),
        "recall_on_scanned_pages": c.recall,
        "scanned_pages": len(c.scanned_pages),
    }


def _short(text: str, n: int = 200) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


def render_markdown(c: Comparison, *, title: str, meta: dict[str, Any]) -> str:
    """Writes the comparison as a readable report with the run details at the top."""
    total = len(c.matches) + len(c.missed)
    lines = [f"# {title}", ""]
    lines += [f"- {k}: {v}" for k, v in meta.items()]
    lines += [
        "",
        "## Read this first",
        "- Hand-coded reasons are a deliberate, selective set. The model proposes every "
        "candidate it finds. **Extras are not necessarily errors**; each needs a person's "
        "judgment.",
        "- A match means the proposed quote overlaps the hand-coded quote on the same PDF "
        "page. It says nothing about the category, which the model does not assign.",
        "- Misses on pages the model never read are listed apart and are not counted.",
        "",
        "## Result",
        f"- Hand-coded reasons found: **{len(c.matches)} of {total}** on scanned pages "
        f"({sum(m.kind == 'same' for m in c.matches)} same, "
        f"{sum(m.kind == 'partial' for m in c.matches)} partial overlap)",
        f"- Missed: {len(c.missed)}",
        f"- Not on a scanned page: {len(c.not_scanned)}",
        f"- Extras to review: {len(c.extras)} "
        f"({sum(e.page_has_hand_coded for e in c.extras)} on pages that also have a "
        f"hand-coded reason)",
        "",
        "## Matched",
    ]
    lines += [
        f"- p{m.hand['pdf_page']} {m.hand['id']} ({m.kind}, {m.score:.2f}): "
        f"{_short(m.hand['quote'])}"
        for m in c.matches
    ] or ["- none"]
    lines += ["", "## Missed"]
    lines += [
        f"- p{m.hand['pdf_page']} {m.id}: {m.why}. {_short(m.hand['quote'])}" for m in c.missed
    ] or ["- none"]
    if c.not_scanned:
        lines += ["", "## Hand-coded, page not scanned"]
        lines += [f"- p{h['pdf_page']} {h['id']}" for h in c.not_scanned]
    lines += ["", "## Extras (proposed, not hand-coded)"]
    lines += [
        f"- p{e.found['pdf_page']} {e.found['id']}"
        f"{' (page has a hand-coded reason)' if e.page_has_hand_coded else ''}: "
        f"{_short(e.found['quote'])}"
        for e in sorted(c.extras, key=lambda e: (e.found["pdf_page"], str(e.found["id"])))
    ] or ["- none"]
    return "\n".join(lines) + "\n"
