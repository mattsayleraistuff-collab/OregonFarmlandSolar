# Methodology and decision record

Purpose: record the reasoning behind analyses and data decisions so the work can be audited and reproduced.

Git history already records what changed, when, and by whom, so this file does not repeat that. Link to the pull request instead.

## How to use this file
Add one entry per decision or analysis, newest at the bottom. Put the entry in the same pull request as the work it explains.

## Entry template
- **Decision or analysis:**
- **Why** (and alternatives rejected):
- **Inputs** (dataset ids from `docs/data-sources.md`):
- **Assumptions and definitions:**
- **Limitations / open questions:**
- **Pull request:**

## Entries

### Initial data model and data-handling rules
- **Decision or analysis:** the data model, reason taxonomy, quote checking and publication policy for the first version.
- **Why (and alternatives rejected):**
  - *Model is project -> proceeding -> document -> reason.* One project passes through several proceedings (staff report, county decision, LUBA appeal, court remand), and a reason belongs to a specific document.
  - *Outcomes are split.* `local_outcome` records what a county decided; `appeal_outcome` records what a reviewing body did. A single "outcome" field was rejected because an appeal result of "affirmed" can mean a denial or an approval stands, so pooling them would mislead. Results are reported per source type (luba / county / efsc), never pooled: LUBA covers appeals only and EFSC covers large projects only.
  - *Taxonomy is a versioned data file* (`data/taxonomy/reasons.yaml`, v1 draft from three sample projects), so categories can be added without schema changes. Ids are never renamed or reused; `other_uncoded` plus a note catches gaps and is reviewed periodically for new categories.
  - *Every coded reason carries a verbatim quote and a PDF page.* The quote is checked against that page's text to catch misquotes and model hallucinations. Fuzzy matches are flagged for a person to review.
  - *Source PDFs stay local.* Published: structured data, quotes with page references, and a manifest with checksums. Republishing the PDFs was rejected because public-records documents can contain personal information. CI therefore verifies synthetic data only.
  - *Synthetic demo data is flagged on every record,* is never mixed with real records, and must be labeled in any UI.
  - *The personal-information scan finds candidates only;* a person reviews quotes before they are published.
- **Inputs:** seven sample PDFs held locally (three projects plus two background documents), to be listed in `docs/data-sources.md`.
- **Assumptions and definitions:** farmland is recorded as the decision itself states it (exclusive farm use or high-value farmland), not re-derived. Dual-use means the decision text mentions grazing, crops or pollinator habitat under or between panels.
- **Limitations / open questions:** the taxonomy is a draft from three projects. Tax-lot matching and parcel-level locations are deferred in favor of a county-level map, and the terms of use for tax lot data are unconfirmed. Quote checking relies on locally extracted text and tolerates ordinary OCR noise but not heavy corruption.
- **Pull request:** #2
