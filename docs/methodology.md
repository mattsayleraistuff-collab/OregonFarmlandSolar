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
### 2026-10-18 - Design decisions before any data coding
- **Unit of analysis:** project -> proceeding -> document -> reason. A project can have several proceedings (staff report, county decision, LUBA appeal, court remand).
- **Outcomes are split.** `local_outcome` (approved / approved_with_conditions / denied) applies to local proceedings; `appeal_outcome` (affirmed / reversed / remanded / dismissed) applies to appeal proceedings. They are never pooled into one "outcome". Source type (luba / county / efsc) is tagged on every project and results are reported per source type.
- **Reason taxonomy** lives in `data/taxonomy/reasons.yaml` (v1, drafted from three sample projects; not comprehensive). Ids are never renamed or reused; retired ids are deprecated with `replaced_by`; every change bumps `version` and adds a changelog line. `other_uncoded` requires a free-text note and is reviewed periodically for new categories.
- **Quote verification:** every coded reason carries a verbatim quote and a 1-based `pdf_page`. `check_quote` confirms the quote appears on that page of the locally extracted text (tolerant of line numbers, hyphenation and OCR noise; fuzzy matches are flagged `exact=False` for review). Tested against LUBA 2018-009: real quotes found on the right pages, an invented quote rejected.
- **Source PDFs stay local.** Only structured data, quotes with page references, and a manifest (document id, SHA-256, type, source) are published. This avoids republishing personal information that may appear in public-records PDFs. Quote verification against the full set therefore runs locally; CI uses synthetic data only.
- **Personal-information scan:** `oregon_farmland_solar.pii` flags emails, phone numbers and SSN-shaped numbers in quotes and notes, plus an optional local-only blocklist. It finds candidates only; quotes are still reviewed by a person before publishing.
- **Synthetic data** is flagged on every record (`synthetic: true`), may not be mixed with real records under one project, and must be labeled in any UI.
- **Known gaps:** tax-lot matching and parcel-level locations are deferred (county-level map first); tax lot data terms of use not yet confirmed.


