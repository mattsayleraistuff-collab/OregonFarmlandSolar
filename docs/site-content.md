# Content the website must carry

A running list of things the public site has to say, not just the repo docs. Add to it when a decision in `docs/methodology.md` affects how a reader should interpret what they see. Check it off in the pull request that builds the page.

| Item | Why it is needed | Source in the repo | Done |
|---|---|---|---|
| Scope statement | The data is county approvals plus three LUBA cases, not all Oregon permits, and not final outcomes. | README "Scope and coverage" | no |
| Synthetic-data label | Demo records are invented and must be marked on every map and chart that uses them. | `docs/methodology.md` (synthetic records entry) | no |
| Result labels: "county outcome" and "appeal outcome (where in our records)" | Never "final", because appeals and court decisions are incomplete. | `docs/methodology.md` (scope entry) | no |
| How LUBA appeals work | A reader must be able to tell what affirmed, reversed and remanded mean for a permit. Cover: remand (the county can fix and decide again, so the project is unresolved) versus reversal (the decision cannot stand as a matter of law), and further review by the Court of Appeals and Supreme Court. Confirm the reverse-versus-remand rule against a primary source before publishing it. | `docs/methodology.md` (LUBA terms) | no |
| Who petitioned changes how to read a LUBA result | A "denied" assignment supports a denial when the applicant appealed and an approval when an opponent appealed. | `docs/methodology.md` (LUBA terms) | no |
| LUBA cases are shown separately, never pooled | They are coded more narrowly (only grounds LUBA upheld). | `docs/methodology.md` (coding rule) | no |
| Machine-extracted versus hand-checked | Once bulk processing exists, reasons not reviewed by a person are labelled. | `hand_checked` field | no |
