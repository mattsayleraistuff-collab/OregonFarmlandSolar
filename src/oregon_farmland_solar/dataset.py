"""Whole-dataset container and cross-record checks."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from .models import REASON_BEARING_TYPES, Document, Proceeding, Project, Reason
from .taxonomy import CATCH_ALL_ID, Taxonomy


class Dataset(BaseModel):
    """All records in one file: projects, proceedings, documents and reasons."""

    model_config = ConfigDict(extra="forbid")

    projects: list[Project] = []
    proceedings: list[Proceeding] = []
    documents: list[Document] = []
    reasons: list[Reason] = []


@dataclass(frozen=True)
class Issue:
    """A problem found while checking records.

    Attributes:
        level: "error" (must fix) or "warning" (review).
        message: Human-readable description naming the record.
    """

    level: str  # "error" | "warning"
    message: str


def load_dataset(path: str | Path) -> Dataset:
    """Loads a records JSON file.

    Args:
        path: Path to the JSON file.

    Returns:
        The parsed Dataset.

    Raises:
        pydantic.ValidationError: If a record has a missing, unknown or invalid field.
    """
    return Dataset.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def check_dataset(ds: Dataset, taxonomy: Taxonomy) -> list[Issue]:
    """Runs the cross-record checks that field validation cannot do.

    Checks for duplicate ids, references to records that do not exist, synthetic flags that
    disagree down the chain, real documents without a checksum, reasons on document types
    that cannot carry them, reasons citing a document from another proceeding or a page past
    the end, categories missing from the taxonomy (deprecated ones warn), and
    ``other_uncoded`` without a note.

    Args:
        ds: Dataset to check.
        taxonomy: Taxonomy the reason categories must come from.

    Returns:
        Issues found, possibly empty.
    """
    issues: list[Issue] = []

    def err(msg: str) -> None:
        issues.append(Issue("error", msg))

    def warn(msg: str) -> None:
        issues.append(Issue("warning", msg))

    tables = {
        "project": ds.projects,
        "proceeding": ds.proceedings,
        "document": ds.documents,
        "reason": ds.reasons,
    }
    for kind, rows in tables.items():
        for row_id, n in Counter(r.id for r in rows).items():
            if n > 1:
                err(f"duplicate {kind} id {row_id!r}")

    projects = {p.id: p for p in ds.projects}
    proceedings = {p.id: p for p in ds.proceedings}
    documents = {d.id: d for d in ds.documents}

    for pr in ds.proceedings:
        project = projects.get(pr.project_id)
        if project is None:
            err(f"proceeding {pr.id!r} references unknown project {pr.project_id!r}")
        elif pr.synthetic != project.synthetic:
            err(f"proceeding {pr.id!r}: synthetic flag differs from its project")

    for doc in ds.documents:
        proc = proceedings.get(doc.proceeding_id)
        if proc is None:
            err(f"document {doc.id!r} references unknown proceeding {doc.proceeding_id!r}")
        elif doc.synthetic != proc.synthetic:
            err(f"document {doc.id!r}: synthetic flag differs from its proceeding")
        if not doc.synthetic and doc.sha256 is None:
            err(f"document {doc.id!r} is real but has no sha256")

    for r in ds.reasons:
        proc = proceedings.get(r.proceeding_id)
        doc = documents.get(r.document_id)
        if proc is None:
            err(f"reason {r.id!r} references unknown proceeding {r.proceeding_id!r}")
        if doc is None:
            err(f"reason {r.id!r} references unknown document {r.document_id!r}")
        if doc is not None:
            if proc is not None and doc.proceeding_id != proc.id:
                err(f"reason {r.id!r}: document {doc.id!r} belongs to {doc.proceeding_id!r}")
            if doc.document_type not in REASON_BEARING_TYPES:
                err(f"reason {r.id!r}: document {doc.id!r} is not a reason-bearing type")
            if r.synthetic != doc.synthetic:
                err(f"reason {r.id!r}: synthetic flag differs from its document")
            if doc.page_count is not None and r.pdf_page > doc.page_count:
                err(f"reason {r.id!r}: pdf_page {r.pdf_page} exceeds page_count")

        entry = taxonomy.get(r.category)
        if entry is None:
            err(f"reason {r.id!r} uses category {r.category!r} that is not in the taxonomy")
        elif entry.status == "deprecated":
            warn(f"reason {r.id!r} uses deprecated category {r.category!r}")
        if r.category == CATCH_ALL_ID and not (r.note and r.note.strip()):
            err(f"reason {r.id!r} uses {CATCH_ALL_ID!r} and needs a note")

    return issues
