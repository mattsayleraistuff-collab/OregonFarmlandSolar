"""Extract candidate reasons from decision PDFs with a local language model.

The model only proposes quotes. Nothing it says is trusted: every quote must be found,
word for word, on the page it came from (``gate_quotes``), and anything that fails is
rejected and kept in the output for audit. Accepted reasons are written as uncoded,
not-hand-checked candidates; a person assigns categories and checks them.

Privacy: source documents may contain personal information, so the pipeline only talks to a
model server on this computer. Models served by a remote service ("cloud" models) are
refused unless the user types a confirmation phrase, or passes an explicit flag in an
unattended run.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .quotes import _squash, check_quote

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODEL = "qwen3:30b-instruct"
DEFAULT_TEMPERATURE = 0
DEFAULT_SEED = 42
MIN_WORDS = 6
MAX_WORDS = 40
CAPS_RATIO = 0.8
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
SOURCES = ("county", "LUBA")
CLOUD_PHRASE = "SEND TO CLOUD"
CLOUD_WARNING = (
    "WARNING: this model runs on a remote service, not on this computer. Every page of text "
    "would be sent over the internet, and the documents may contain personal information "
    "(names, addresses, phone numbers). You are responsible for that disclosure.\n"
    f"Type {CLOUD_PHRASE} to continue, anything else to stop: "
)


class LocalOnlyError(Exception):
    """Raised when the model or server is not on this computer, or the model is missing."""


class CloudModelRefused(LocalOnlyError):
    """Raised when a cloud model is chosen and the user did not confirm."""


# ---- prompt ------------------------------------------------------------------------------


def load_prompt(path: Path) -> tuple[str, str]:
    """Reads a prompt file.

    Args:
        path: The prompt text file (it must end where the page text is appended).

    Returns:
        The prompt text and the SHA-256 of the file's bytes, which the run manifest records.
    """
    raw = path.read_bytes()
    return raw.decode("utf-8"), hashlib.sha256(raw).hexdigest()


def build_prompt(prompt_text: str, page_text: str) -> str:
    """Appends one page of text to the prompt."""
    return prompt_text + page_text


# ---- parsing and the quote gate ----------------------------------------------------------


@dataclass(frozen=True)
class RawReason:
    """A reason as proposed by the model.

    Attributes:
        quote: The model's quote (unverified).
        source: "county" or "LUBA", as the model labeled it (unverified).
    """

    quote: str
    source: str


@dataclass(frozen=True)
class ParsedResponse:
    """The model's reply after structural checks.

    Attributes:
        has_reasons: The model's own yes/no answer.
        reasons: Proposed reasons (empty if the reply was malformed).
        error: Why the reply was unusable, or None.
    """

    has_reasons: bool
    reasons: list[RawReason]
    error: str | None = None


def parse_response(text: str) -> ParsedResponse:
    """Checks the shape of the model's JSON reply without guessing at repairs.

    Args:
        text: The raw reply.

    Returns:
        A ParsedResponse; ``error`` is set (and ``reasons`` empty) if anything is off.
    """

    def bad(msg: str) -> ParsedResponse:
        return ParsedResponse(False, [], msg)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return bad(f"not valid JSON: {e.msg}")
    if not isinstance(data, dict):
        return bad("reply is not a JSON object")
    flag, items = data.get("has_reasons"), data.get("reasons")
    if not isinstance(flag, bool):
        return bad("has_reasons is missing or not true/false")
    if not isinstance(items, list):
        return bad("reasons is missing or not a list")
    out: list[RawReason] = []
    for item in items:
        if not isinstance(item, dict):
            return bad("a reason is not an object")
        quote, source = item.get("quote"), item.get("source")
        if not isinstance(quote, str) or not quote.strip():
            return bad("a reason has no quote text")
        if source not in SOURCES:
            return bad(f"a reason has source {source!r}, expected one of {SOURCES}")
        out.append(RawReason(quote=quote.strip(), source=source))
    if flag != bool(out):
        return bad("has_reasons contradicts the reasons list")
    return ParsedResponse(flag, out)


@dataclass(frozen=True)
class GatedQuote:
    """A proposed quote after the checks.

    Attributes:
        quote: The quote text.
        source: "county" or "LUBA" as the model labeled it.
        status: "accepted" (exact match), "review" (fuzzy match; a person must check) or
            "rejected".
        reason: Why it was not accepted (None if accepted).
        score: Match score from ``check_quote`` (0 if not found).
        position: Where the quote starts in the page's normalized text (for stable ordering).
    """

    quote: str
    source: str
    status: str
    reason: str | None = None
    score: float = 0.0
    position: int = 0


def _letters_upper_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    return sum(c.isupper() for c in letters) / len(letters) if letters else 0.0


def gate_quotes(reasons: Sequence[RawReason], page_text: str) -> list[GatedQuote]:
    """Checks each proposed quote against the page it came from.

    Rejected: too short or too long, mostly capitals (headings and disposition lines), not
    on the page, or a repeat of an earlier quote. A fuzzy match goes to "review".

    Args:
        reasons: Proposed reasons from one page.
        page_text: The extracted text of that page.

    Returns:
        One GatedQuote per input, in input order.
    """
    page_norm = _squash(page_text, strip_line_numbers=True)
    seen: set[str] = set()
    out: list[GatedQuote] = []
    for r in reasons:
        norm = _squash(r.quote, strip_line_numbers=False)
        words = len(r.quote.split())

        def reject(why: str, *, r: RawReason = r) -> GatedQuote:
            return GatedQuote(r.quote, r.source, "rejected", why)

        if norm in seen:
            out.append(reject("duplicate"))
        elif words < MIN_WORDS:
            out.append(reject("too_short"))
        elif words > MAX_WORDS:
            out.append(reject("too_long"))
        elif _letters_upper_ratio(r.quote) >= CAPS_RATIO:
            out.append(reject("all_caps"))
        else:
            chk = check_quote(r.quote, page_text)
            if not chk.found:
                out.append(reject("not_on_page"))
            else:
                pos = page_norm.find(norm[:30])
                status, why = ("accepted", None) if chk.exact else ("review", "fuzzy_match")
                out.append(GatedQuote(r.quote, r.source, status, why, chk.score, max(pos, 0)))
        seen.add(norm)
    return out


# ---- local-only guard --------------------------------------------------------------------


@dataclass(frozen=True)
class ModelInfo:
    """A model known to the local server.

    Attributes:
        name: The model tag, e.g. ``qwen3:30b-instruct``.
        digest: The server's content digest of the model weights.
        remote: True if the server reports it as served remotely (a cloud model).
    """

    name: str
    digest: str
    remote: bool = False


def is_cloud(model: ModelInfo | str) -> bool:
    """True if the model is served by a remote service rather than run locally."""
    if isinstance(model, ModelInfo):
        return model.remote or is_cloud(model.name)
    return model.endswith(("-cloud", ":cloud"))


def check_host(host: str) -> None:
    """Raises LocalOnlyError unless the server address is this computer."""
    name = urlparse(host).hostname
    if name not in LOCAL_HOSTS:
        raise LocalOnlyError(f"model server {host!r} is not on this computer")


def check_model(
    name: str,
    models: Sequence[ModelInfo],
    *,
    allow_cloud: bool,
    confirm: Callable[[str], str] | None,
) -> ModelInfo:
    """Checks that the chosen model may be used.

    Args:
        name: The model tag the user chose.
        models: Models the local server reports.
        allow_cloud: True if the user passed the explicit flag for unattended cloud use.
        confirm: Shows a warning and returns what the user typed; None if no one can answer.

    Returns:
        The model's info.

    Raises:
        LocalOnlyError: If the model is not installed.
        CloudModelRefused: If it is a cloud model and the user did not confirm.
    """
    found = next((m for m in models if m.name == name), None)
    if found is None and is_cloud(name):
        found = ModelInfo(name=name, digest="", remote=True)
    if found is None:
        raise LocalOnlyError(f"model {name!r} is not installed locally (try: ollama pull {name})")
    if is_cloud(found) and not allow_cloud:
        if confirm is None:
            raise CloudModelRefused(
                f"{name!r} is a cloud model; pass --allow-cloud to use it in an unattended run"
            )
        if confirm(CLOUD_WARNING).strip() != CLOUD_PHRASE:
            raise CloudModelRefused(f"cloud model {name!r} not confirmed")
    return found


# ---- talking to the model ----------------------------------------------------------------


def build_request(model: str, prompt: str, *, temperature: float, seed: int) -> dict[str, Any]:
    """Builds the request body for the local server's generate endpoint."""
    return {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": temperature, "seed": seed},
    }


def list_models(host: str) -> list[ModelInfo]:
    """Asks the local server which models it has.

    Args:
        host: Server address (must be this computer).

    Returns:
        The installed models.
    """
    check_host(host)
    with urllib.request.urlopen(host.rstrip("/") + "/api/tags", timeout=10) as resp:  # noqa: S310
        data = json.load(resp)
    return [
        ModelInfo(
            name=m["name"],
            digest=m.get("digest", ""),
            remote=bool(m.get("remote_host") or m.get("remote_model")),
        )
        for m in data.get("models", [])
    ]


def make_sender(host: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Returns a function that sends one request to the local server and returns its reply."""
    check_host(host)

    def send(request: dict[str, Any]) -> dict[str, Any]:
        req = urllib.request.Request(  # noqa: S310
            host.rstrip("/") + "/api/generate",
            data=json.dumps(request).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=600) as resp:  # noqa: S310
            return json.load(resp)

    return send


# ---- running a document ------------------------------------------------------------------


@dataclass
class PageResult:
    """What came out of one page.

    Attributes:
        page: 1-based PDF page number.
        skipped: "blank" if the page had no text and the model was not called.
        error: Why the model's reply was unusable, or None.
        has_reasons: The model's own yes/no for the page.
        accepted: Quotes found exactly on the page.
        review: Quotes found only by fuzzy match.
        rejected: Quotes that failed a check (kept for audit).
    """

    page: int
    skipped: str | None = None
    error: str | None = None
    has_reasons: bool = False
    accepted: list[GatedQuote] = field(default_factory=list)
    review: list[GatedQuote] = field(default_factory=list)
    rejected: list[GatedQuote] = field(default_factory=list)


@dataclass(frozen=True)
class ExtractedReason:
    """An accepted candidate reason with its stable id."""

    id: str
    document_id: str
    page: int
    quote: str
    source: str


@dataclass
class DocumentResult:
    """All pages of one document.

    Attributes:
        doc_id: Document id.
        pdf_sha256: Checksum of the source PDF.
        pages: Per-page results in page order.
    """

    doc_id: str
    pdf_sha256: str
    pages: list[PageResult]

    def reasons(self) -> list[ExtractedReason]:
        """Accepted reasons ordered by page then position, with ids assigned after sorting."""
        out: list[ExtractedReason] = []
        for p in self.pages:
            ordered = sorted(p.accepted, key=lambda g: g.position)
            for n, g in enumerate(ordered, start=1):
                rid = f"{self.doc_id}-p{p.page}-r{n}"
                out.append(ExtractedReason(rid, self.doc_id, p.page, g.quote, g.source))
        return out


def run_document(
    *,
    doc_id: str,
    pdf_sha256: str,
    pages: Sequence[str],
    prompt_text: str,
    model: ModelInfo,
    send: Callable[[dict[str, Any]], dict[str, Any]],
    temperature: float = DEFAULT_TEMPERATURE,
    seed: int = DEFAULT_SEED,
) -> DocumentResult:
    """Runs the model over every page of one document and gates the results.

    Args:
        doc_id: Document id used in reason ids.
        pdf_sha256: Checksum of the source PDF.
        pages: Page texts in order.
        prompt_text: The prompt (ends where the page text goes).
        model: The model to use (already checked).
        send: Function that sends a request and returns the server's reply.
        temperature: Sampling temperature (0 for repeatable output).
        seed: Random seed.

    Returns:
        A DocumentResult. Unusable replies are recorded on the page, not raised.
    """
    results: list[PageResult] = []
    for number, text in enumerate(pages, start=1):
        res = PageResult(page=number)
        results.append(res)
        if not text.strip():
            res.skipped = "blank"
            continue
        request = build_request(
            model.name, build_prompt(prompt_text, text), temperature=temperature, seed=seed
        )
        parsed = parse_response(send(request).get("response", ""))
        if parsed.error:
            res.error = parsed.error
            continue
        res.has_reasons = parsed.has_reasons
        for g in gate_quotes(parsed.reasons, text):
            {"accepted": res.accepted, "review": res.review, "rejected": res.rejected}[
                g.status
            ].append(g)
    return DocumentResult(doc_id, pdf_sha256, results)


# ---- outputs -----------------------------------------------------------------------------


def _quote_view(doc_id: str, page: int, g: GatedQuote) -> dict[str, Any]:
    return {
        "document_id": doc_id,
        "pdf_page": page,
        "quote": g.quote,
        "machine_source": g.source,
        "status": g.status,
        "reason": g.reason,
        "score": g.score,
    }


def output_document(res: DocumentResult) -> dict[str, Any]:
    """Builds the JSON output: candidate reasons plus everything held back, for audit.

    Accepted reasons are uncoded (``other_uncoded``) and not hand-checked; they are
    candidates for a person to categorize and verify, never final records.
    """
    return {
        "document_id": res.doc_id,
        "reasons": [
            {
                "id": r.id,
                "document_id": r.document_id,
                "pdf_page": r.page,
                "quote": r.quote,
                "machine_source": r.source,
                "category": "other_uncoded",
                "hand_checked": False,
            }
            for r in res.reasons()
        ],
        "needs_review": [_quote_view(res.doc_id, p.page, g) for p in res.pages for g in p.review],
        "rejected": [_quote_view(res.doc_id, p.page, g) for p in res.pages for g in p.rejected],
        "page_errors": [
            {"pdf_page": p.page, "error": p.error} for p in res.pages if p.error is not None
        ],
    }


def build_manifest(
    res: DocumentResult,
    *,
    pipeline_commit: str,
    prompt_sha256: str,
    model: ModelInfo,
    temperature: float,
    seed: int,
    host: str,
    cloud: bool,
    run_at: str,
) -> dict[str, Any]:
    """Records what is needed to repeat and audit a run: "pipeline X ran on input Y".

    Args:
        res: The run's result.
        pipeline_commit: Git commit of the pipeline code.
        prompt_sha256: Checksum of the prompt file.
        model: The model used (its digest identifies the exact weights).
        temperature: Sampling temperature used.
        seed: Seed used.
        host: Server address used.
        cloud: True if a cloud model was used.
        run_at: ISO timestamp of the run.

    Returns:
        A JSON-compatible dict, including a checksum of the output.
    """
    out = output_document(res)
    canonical = json.dumps(out, sort_keys=True, ensure_ascii=False).encode()
    return {
        "pipeline_commit": pipeline_commit,
        "run_at": run_at,
        "prompt_sha256": prompt_sha256,
        "model": {"name": model.name, "digest": model.digest},
        "settings": {"temperature": temperature, "seed": seed},
        "host": host,
        "cloud": cloud,
        "input": {
            "document_id": res.doc_id,
            "pdf_sha256": res.pdf_sha256,
            "page_count": len(res.pages),
            "scanned_pages": [p.page for p in res.pages if p.skipped is None],
        },
        "counts": {
            "accepted": sum(len(p.accepted) for p in res.pages),
            "review": sum(len(p.review) for p in res.pages),
            "rejected": sum(len(p.rejected) for p in res.pages),
            "page_errors": sum(p.error is not None for p in res.pages),
        },
        "output_sha256": hashlib.sha256(canonical).hexdigest(),
    }
