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
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    # True for invented demo records; they must never be mixed with real ones.
    synthetic: bool = False


class SourceType(StrEnum):
    LUBA = "luba"
    COUNTY = "county"
    EFSC = "efsc"
    OTHER = "other"


class Level(StrEnum):
    LOCAL = "local"
    APPEAL = "appeal"


class LocalOutcome(StrEnum):
    APPROVED = "approved"
    APPROVED_WITH_CONDITIONS = "approved_with_conditions"
    DENIED = "denied"


class AppealOutcome(StrEnum):
    AFFIRMED = "affirmed"
    REVERSED = "reversed"
    REMANDED = "remanded"
    DISMISSED = "dismissed"


class DocumentType(StrEnum):
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
    name: str = Field(min_length=1)
    county: str = Field(min_length=1)
    source_type: SourceType
    acres: float | None = Field(default=None, gt=0)
    # Recorded as the decision states it; not re-derived.
    land_class_as_stated: str | None = None
    dual_use: bool | None = None


class Proceeding(_Record):
    project_id: str
    level: Level
    body: str = Field(min_length=1)
    decision_date: date | None = None
    citation: str | None = None
    local_outcome: LocalOutcome | None = None
    appeal_outcome: AppealOutcome | None = None

    @model_validator(mode="after")
    def _outcome_matches_level(self) -> Proceeding:
        if self.level is Level.LOCAL:
            if self.local_outcome is None or self.appeal_outcome is not None:
                raise ValueError("a local proceeding needs local_outcome and no appeal_outcome")
        elif self.appeal_outcome is None or self.local_outcome is not None:
            raise ValueError("an appeal proceeding needs appeal_outcome and no local_outcome")
        return self


class Document(_Record):
    proceeding_id: str
    document_type: DocumentType
    # Required for real documents (checked in check_dataset); SHA-256 of the original file.
    sha256: str | None = None
    source_url: str | None = None
    page_count: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _sha_format(self) -> Document:
        if self.sha256 is not None and not _SHA256_RE.fullmatch(self.sha256):
            raise ValueError("sha256 must be 64 lowercase hex characters")
        return self


class Reason(_Record):
    proceeding_id: str
    document_id: str
    category: str = Field(min_length=1)
    quote: str = Field(min_length=1)
    # 1-based index of the page within the PDF (not the number printed on the page).
    pdf_page: int = Field(ge=1)
    printed_page: str | None = None
    note: str | None = None
    hand_checked: bool = False
