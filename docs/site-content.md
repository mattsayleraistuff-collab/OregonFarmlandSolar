# Content the website must carry

A running list of things the public site has to say, not just the repo docs. Add to it when a decision in `docs/methodology.md` affects how a reader should interpret what they see. Check it off in the pull request that builds the page.

| Item | Why it is needed | Source in the repo | Done |
|---|---|---|---|
| Scope statement | The data is county approvals plus three LUBA cases (two county denials and one reversed approval), not all Oregon permits, and not final outcomes. | README "Scope and coverage" | no |
| Synthetic-data label | Demo records are invented and must be marked on every map and chart that uses them. | `docs/methodology.md` (synthetic records entry) | no |
| Result labels: "county outcome" and "appeal outcome (where in our records)" | Never "final", because appeals and court decisions are incomplete. | `docs/methodology.md` (scope entry) | no |
| How LUBA appeals work | A reader must be able to tell what affirmed, reversed and remanded mean for a permit. Cover: remand (the county can fix and decide again, so the project is unresolved) versus reversal (the decision cannot stand as a matter of law), and further review by the Court of Appeals and Supreme Court. Reverse-versus-remand rule confirmed against OAR 661-010-0071 on 2026-10-21 (see methodology). | `docs/methodology.md` (LUBA terms) | yes |
| Who petitioned changes how to read a LUBA result | A "denied" assignment supports a denial when the applicant appealed and an approval when an opponent appealed. | `docs/methodology.md` (LUBA terms) | no |
| LUBA cases are shown separately, never pooled | They are coded more narrowly (only grounds LUBA upheld). | `docs/methodology.md` (coding rule) | no |
| Machine-extracted versus hand-checked | Once bulk processing exists, reasons not reviewed by a person are labelled. | `hand_checked` field | no |
| Boundary credit and generalization | Credit "Bureau of Land Management (BLM), Oregon State Office" where the county layer is shown, and say the boundaries are for display and are not legal boundaries or surveys. | `data/geo/oregon-counties.provenance.json` | no |
| Check the LUBA explainer wording | The 21-day deadline, who can appeal, what LUBA reviews, and the affirm / reverse / remand / dismiss meanings were checked on 2026-10-21 against LUBA's FAQ (given by Matt) and OAR 661-010-0071 (official Secretary of State page, last amended effective 2024-01-01). Re-check the FAQ link before launch. | `site/index.html` (How appeals work) | yes |
| Check the county-records source wording | The page says the approvals are "provided by the State of Oregon" and "from the state's list". Confirm this matches how the records were actually obtained. | `site/index.html` (Method and credits, Overview) | no |
| Decide whether to show reviewer notes | Notes on reasons are internal coding context and are not shown on the site. A public-facing note field would be needed to show any. | `data/records/*.json` (`note`) | no |
| Reason category names | The site shows the taxonomy labels (for example "No local code authority for the use"), which differ slightly from the shorter names in the design guide. | `data/taxonomy/reasons.yaml` | no |
| Screen-reader test | Contrast was checked by formula and the keyboard path by script. Nobody has used the page with NVDA or VoiceOver yet. | `design/accessibility.md` | no |
