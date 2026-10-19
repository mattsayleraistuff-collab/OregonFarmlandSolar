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

### Hand-coding sample records: Marion County (Silver Creek Solar)
- **Decision or analysis:** first hand-coded project (`data/records/marion-silver-creek-solar.json`): a staff report and the LUBA 2023-045 opinion, coded into 5 reasons. Added a `validate` command (`uv run ofs validate`) that runs the data checks, the personal-information scan, and, given a local PDF folder, checks every quote against the cited page of the PDF with the matching sha256.
- **Why (and alternatives rejected):**
  - *Reasons are attached to the proceeding whose document they appear in.* The county board's own decision was not in the sample set, so the board's grounds are coded from LUBA's summary and sit under the appeal proceeding, with a note. Alternative (open): allow a reason to explain an earlier proceeding than its document belongs to.
  - *The staff report is coded under the local proceeding but is a recommendation, not the decision;* the reason's note says so.
  - *Phone-number pattern excludes Oregon rule numbers* (for example OAR 660-033-0130(38)); they have the same shape as phone numbers and caused false positives.
- **Inputs:** the two Marion County documents listed in `docs/data-sources.md`.
- **Assumptions and definitions:** the local outcome (denied) comes from the LUBA opinion's description of the board decision; the board decision date is not stated in the sample and is left empty. Coded reasons are not yet `hand_checked`.
- **Limitations / open questions:** the sample has only one reason category pair (state standards, no local authority); the taxonomy has no category for "local code repealed" vs. "state rule applies directly". Review pending.
- **Pull request:** to be added

### Hand-coding sample records: Yamhill County (Yamhill Creek Solar)
- **Decision or analysis:** second hand-coded project (`data/records/yamhill-creek-solar.json`): the LUBA 2018-009 opinion, coded into 6 reasons (5 are the county board's grounds for denial as quoted or summarized by LUBA, 1 is LUBA's reason for affirming). Added `tests/test_records.py` so every committed records file is validated (structure, taxonomy, personal-information scan) in CI.
- **Why (and alternatives rejected):**
  - *Only the board's final order is recorded as the local proceeding.* The planning commission approved the application first and the board reversed it 2-1 on appeal; no document for the planning commission decision is in the sample, so it is not recorded.
  - *Coded a subset of the county's grounds.* The board denied on six approval standards and weighed more than two dozen plan policies; LUBA upheld one sufficient basis (plan consistency) and did not rule on the rest. The reasons coded are the main distinct grounds, not every sub-finding.
  - *Same convention as Marion:* the board's grounds sit under the appeal proceeding because LUBA's opinion is the document that quotes them (open design question, see the Marion entry).
- **Inputs:** `LUBA_18009_2018.pdf` (see `docs/data-sources.md`).
- **Assumptions and definitions:** `acres` is the 27.8-acre parcel; the facility is 12 acres. Land class is recorded as stated (EFU, high-value farmland by viticulture area).
- **Limitations / open questions:** two reasons use `other_uncoded` (siting outside an urban growth boundary without a buffer; LUBA deference to the county's weighing). If these recur in the full records, they are candidates for new taxonomy categories. Reasons are not yet `hand_checked`.
- **Pull request:** to be added

### A reason belongs to the decision it explains, not the document that quotes it
- **Decision or analysis:** `Reason.proceeding_id` is the proceeding whose outcome the reason explains. A reason for the county's decision stays under the local proceeding even when the only source is a LUBA opinion quoting the county's findings; LUBA's own reasons for affirming, reversing or remanding stay under the appeal proceeding. This supersedes the convention used in the Marion and Yamhill entries above.
- **Why (and alternatives rejected):** the dashboard counts the county's grounds for approval or denial, and in the sample set those grounds are available only as LUBA quotes them. Attaching them to the appeal would drop them from county-level counts. The alternative (a second field marking "reasons for the local decision") was rejected as redundant: the proceeding and the document already say which decision a reason explains and where the text was found.
- **Assumptions and definitions:** an appeal document may supply reasons for the local proceeding of the same project; no other cross-proceeding link is allowed (a county document cannot explain an appeal, and nothing crosses projects). `validate` enforces this.
- **Limitations / open questions:** a reason quoted second-hand by LUBA is LUBA's characterization of the county's finding, so the note on each such reason says so. Where the county's own decision is later obtained, its reasons should be coded from that document and the LUBA-quoted duplicates removed.
- **Pull request:** to be added

### Scope: report what the records show, not final outcomes
- **Decision or analysis:** the project reports reasons found in the decisions we hold. It does not claim to report final outcomes or to cover all solar-on-farmland permits in Oregon. Two result labels are used everywhere: "county outcome" (headline) and "appeal outcome (where in our records)".
- **Why (and alternatives rejected):** the records request covers county decisions, and the LUBA opinions were collected by hand, so appeals and court decisions are incomplete. A county approval that LUBA later reversed, or a denial remanded and later approved, would be mislabeled by a "final outcome" field. Collecting the missing appeals and court decisions was rejected for the sprint: with 200+ documents expected, it cannot be done in the time available. A later targeted lookup of LUBA opinions for appealed projects is possible follow-up work.
- **Assumptions and definitions:** the county outcome is the outcome of the local proceeding; the appeal outcome is the outcome of the appeal proceeding in our records, if any. Remanded appeals are unresolved. Where the records request shows a decision was appealed but we hold no appeal document, the project is shown with no appeal outcome, not as final.
- **Limitations / open questions:** selection bias is likely (LUBA samples are appealed cases; the records request may over- or under-represent approvals). Check what the request returns when the files arrive, including any field recording that a decision was appealed.

### Coding rule for LUBA-sourced reasons: only grounds LUBA reviewed and upheld
- **Decision or analysis:** when the source is a LUBA opinion, code only the county grounds that LUBA reviewed and sustained. Where LUBA affirmed on one sufficient basis and did not rule on the county's other grounds, the unreviewed grounds are not coded; this entry records that they exist.
- **Why (and alternatives rejected):** LUBA affirms a denial if at least one ground survives and does not rule on the rest (it would be an advisory opinion). A ground LUBA never reached is untested, not validated, so coding it alongside upheld grounds would suggest it carried the same weight. Coding every county ground, as will be done for un-appealed county decisions, was rejected for the LUBA cases to keep them to what actually decided the outcome. A per-reason "upheld / not reached" field was rejected as unnecessary under this rule.
- **Applied to:** Yamhill Creek Solar. The county denied on six approval standards (OAR 660-033-0130(38)(f)(B) and (C); YCZO 1202.02(B), 1202.02(D), 1202.02(F); YCZO 1101.02(A)(4)). LUBA reviewed only YCZO 1202.02(B) (consistency with comprehensive plan goals and policies, weighed together) and upheld it, so the grounds coded are the findings under that standard. The soil-compaction reason (yamhill-r2) was swapped from the state-standard finding, which LUBA did not review, to the county's finding under the plan's soil-resources goal, which LUBA upheld. The summary "On balance" conclusion restates the individual findings and is not coded separately (see the one-reason-per-ground rule below).
- **Coding rule (all sources):** one reason per distinct ground; a summary or conclusion is coded only if it adds a ground the details do not.
- **Limitations / open questions:** the LUBA cases are coded more narrowly than un-appealed county decisions will be, so they are reported separately and never pooled. Yamhill r1 was swapped from the overall "on balance" conclusion to the separate "can be located on non-farmland" ground in the same final-weighing section.
- **Pull request:** to be added

### Scope update: county records are approvals only (confirmed by the agency)
- **Decision or analysis:** the county-level data is treated as approved decisions only. This replaces the earlier assumption (unconfirmed) in the scope entry above. The README scope statement is updated to match.
- **Why (and alternatives rejected):** the agency's reply to the records request states that the dataset does not include denied or withdrawn applications, and that the PDFs are for approved decisions only. The alternative, presenting the county records as a mix of outcomes, was rejected because the records contain no denials by construction (selection on outcome).
- **Inputs:** the agency's reply to the records request (held locally; not in the repository).
- **Assumptions and definitions:** "approved" includes decisions that may have been appealed or remanded before approval; the history before approval is not in the records. The agency's dataset was built from the PDFs, so the spreadsheet and PDFs describe the same decisions. County records have no local decision numbers, so rows cannot be tied to a specific PDF by number.
- **Limitations / open questions:** denial reasoning exists in the data only for the three LUBA sample cases, so no comparison of approvals and denials is possible and no approval rates can be computed. The reason taxonomy was drafted from denial grounds and will need a stance (supports approval, supports denial, condition) and approval-oriented categories once approval documents or the spreadsheet columns are seen. The records request is a single request: the agency releases nothing until it is complete and paid, but will send the spreadsheet immediately if the PDF portion is withdrawn.
- **Pull request:** to be added
