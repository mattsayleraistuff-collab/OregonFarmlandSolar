"""Record types: project -> proceeding -> document -> reason.

A project can pass through several proceedings (staff report, county decision, LUBA appeal,
court remand ...). Each proceeding has one or more documents, and reasons are coded against a
specific document with a verbatim quote and page reference.

Outcomes are split on purpose: a *local* proceeding records what the county decided
(approved/denied); an *appeal* proceeding records what the reviewing body did (affirmed,
reversed, remanded). They are not interchangeable.
"""

from __future__ import annotations

import re
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

_SHA256_RE = re.compile(r"[0-9a-f]{64}")


class _Record(BaseModel):
    """Base for every record type: a required id and the synthetic flag.

    Unknown fields are rejected (``extra="forbid"``) so a typo in a records file is an error
    instead of silently dropped data.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    # True for invented demo records; they must never be mixed with real ones.
    synthetic: bool = False


class SourceType(StrEnum):
    """Where a project's records came from; results are reported per source, never pooled."""

    LUBA = "luba"
    COUNTY = "county"
    EFSC = "efsc"
    OTHER = "other"


class Level(StrEnum):
    """Whether a proceeding is a local decision or a review of one."""

    LOCAL = "local"
    APPEAL = "appeal"


class LocalOutcome(StrEnum):
    """What a county (or other local body) decided."""

    APPROVED = "approved"
    APPROVED_WITH_CONDITIONS = "approved_with_conditions"
    DENIED = "denied"


class AppealOutcome(StrEnum):
    """What a reviewing body (for example LUBA) did with a local decision."""

    AFFIRMED = "affirmed"
    REVERSED = "reversed"
    REMANDED = "remanded"
    DISMISSED = "dismissed"


class DocumentType(StrEnum):
    """Kind of source document; only some kinds can carry coded reasons."""

    COUNTY_DECISION = "county_decision"
    STAFF_REPORT = "staff_report"
    APPELLATE_OPINION = "appellate_opinion"
    EFSC_ORDER = "efsc_order"
    ADVOCACY_COMMENT = "advocacy_comment"
    LEGAL_DIGEST = "legal_digest"
    OTHER = "other"


# Only these document types can carry coded reasons for a decision.
REASON_BEARING_TYPES = frozenset(
    {
        DocumentType.COUNTY_DECISION,
        DocumentType.STAFF_REPORT,
        DocumentType.APPELLATE_OPINION,
        DocumentType.EFSC_ORDER,
    }
)


class Project(_Record):
    """A proposed solar facility.

    Attributes:
        name: Project name as it appears in the source documents.
        county: Oregon county containing the site.
        source_type: Which kind of source the project was found in.
        acres: Size of the parcel (or facility) in acres, if stated.
        land_class_as_stated: Land classification exactly as the decision states it. Not
            re-derived from soil or zoning data.
        dual_use: True if the decision mentions grazing, crops or pollinator habitat under or
            between panels; None if unknown.
    """

    name: str = Field(min_length=1)
    county: str = Field(min_length=1)
    source_type: SourceType
    acres: float | None = Field(default=None, gt=0)
    # Recorded as the decision states it; not re-derived.
    land_class_as_stated: str | None = None
    dual_use: bool | None = None


class Proceeding(_Record):
    """One decision step for a project (county decision, LUBA appeal, court remand ...).

    A local proceeding must have ``local_outcome`` and no ``appeal_outcome``; an appeal
    proceeding must have the reverse.

    Attributes:
        project_id: Id of the owning Project.
        level: Local decision or appeal.
        body: Deciding body, for example "Marion County Board of Commissioners".
        decision_date: Date of the decision, if known.
        citation: Case or file number, for example "LUBA No. 2023-045" or "CU 22-041".
        local_outcome: Outcome of a local proceeding.
        appeal_outcome: Outcome of an appeal proceeding.
    """

    project_id: str
    level: Level
    body: str = Field(min_length=1)
    decision_date: date | None = None
    citation: str | None = None
    local_outcome: LocalOutcome | None = None
    appeal_outcome: AppealOutcome | None = None

    @model_validator(mode="after")
    def _outcome_matches_level(self) -> Proceeding:
        """Require the outcome field that matches ``level`` and forbid the other."""
        if self.level is Level.LOCAL:
            if self.local_outcome is None or self.appeal_outcome is not None:
                raise ValueError("a local proceeding needs local_outcome and no appeal_outcome")
        elif self.appeal_outcome is None or self.local_outcome is not None:
            raise ValueError("an appeal proceeding needs appeal_outcome and no local_outcome")
        return self


class Document(_Record):
    """A source document belonging to one proceeding.

    Attributes:
        proceeding_id: Id of the owning Proceeding.
        document_type: Kind of document.
        sha256: SHA-256 of the original file; required for real documents so a quote can be
            traced to an exact file.
        file_name: Name of the PDF in the local ``data/raw`` folder. Informational only (the
            checksum is what matches a file); it lets a person find the file for a record.
        source_url: Where the document was obtained, if known.
        page_count: Number of pages in the PDF.
    """

    proceeding_id: str
    document_type: DocumentType
    # Required for real documents (checked in check_dataset); SHA-256 of the original file.
    sha256: str | None = None
    file_name: str | None = None
    source_url: str | None = None
    page_count: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _sha_format(self) -> Document:
        """Reject a sha256 that is not 64 lowercase hex characters."""
        if self.sha256 is not None and not _SHA256_RE.fullmatch(self.sha256):
            raise ValueError("sha256 must be 64 lowercase hex characters")
        return self


class Reason(_Record):
    """One coded reason for (or against) a decision, backed by a verbatim quote.

    Attributes:
        proceeding_id: Id of the Proceeding the reason belongs to.
        document_id: Id of the Document the quote comes from.
        category: Id of an entry in the reason taxonomy.
        quote: Verbatim text from the document, checked against the cited page.
        pdf_page: 1-based index of the page within the PDF (not the printed page number).
        printed_page: Page number printed on the page, if different or useful.
        note: Context for a reviewer; required when the category is ``other_uncoded``.
        hand_checked: True once a person has verified the category and quote.
    """

    proceeding_id: str
    document_id: str
    category: str = Field(min_length=1)
    quote: str = Field(min_length=1)
    # 1-based index of the page within the PDF (not the number printed on the page).
    pdf_page: int = Field(ge=1)
    printed_page: str | None = None
    note: str | None = None
    hand_checked: bool = False
