# Accessibility decisions and open questions

Target: WCAG 2.2 AA. The numbers are in `contrast.md`.

## Decisions

1. **Contrast.** All text is 6.8:1 or better except button and map-label text (5.1:1 minimum). Control edges, focus rings and notice borders are 4.4:1 or better, over the 3:1 required.
2. **Focus ring.** One solid 3px ring in an orange (light) or amber (dark) used for nothing else, with a 2px gap so it always sits on the page ground. It is distinct from the blue of controls. Counties switch their outline to the same colour.
3. **No meaning by colour alone.** Outcomes have an icon and a word. Provenance differs by border style and icon. Counts are printed on counties and in a table. Categories have a glyph, a name and a number. County versus appeal reasons differ by solid versus hatched fill.
4. **Colour-blind-safe palettes.** Okabe and Ito categories and ColorBrewer Blues. Approved and denied use blue and orange rather than green and red. Minimum separation figures are in `contrast.md`.
5. **"No data" is not "none".** While approvals are missing, the map hatching, legend and a notice say "not loaded yet"; table cells show a dash, not 0. Once loaded, a county with none says "No approvals in our records". For county records the appeal column is omitted rather than shown as 0, because appeals are not tracked.
6. **Map has a non-visual twin.** Every county is a link with an `aria-label` that says its count. A county select and a full table of the same counts sit beside the map. The reasons chart always has a table view.
7. **Keyboard.** All controls reachable in DOM order. Skip link first. The map collapses its 36 stops into one with arrow-key movement (roving tabindex), Enter selects, Escape returns to the select. Tables scroll in a focusable, labelled region.
8. **Data-mode switch is a radio group** (fieldset, legend, native radios), not a toggle button. County records and LUBA appeal examples are separate panels with their own headings, so no source-type switch is needed. Selection shows a check icon and fill. Changes announce through a polite live region.
9. **Synthetic data cannot be mistaken for findings.** Sticky banner with `role="status"`, hazard stripes, tag and frame on every data panel, title prefix, and mode kept in the URL.
10. **Light and dark.** Follow the OS by default, a stored override is optional. Every pairing is checked in both themes. The banner stays yellow in both so it cannot be missed.
11. **Reduced motion.** No animation depends on motion; transitions are removed under `prefers-reduced-motion: reduce`.
12. **Forced colours.** Focus outline becomes `Highlight`; controls keep a visible border.
13. **Touch.** Every control is at least 44px tall (WCAG 2.2 asks 24px). Count labels on the map are hidden under 640px because they would render under 8px; the table and county panel carry the numbers.
14. **Text.** 16px body, 14px minimum, line height 1.5, 68ch maximum measure, text resizes to 200% without loss because layout uses container queries and wrapping, not fixed heights.
15. **Plain language.** Notices say what the data is and is not; the explainer uses short steps.

## Things I was unsure about

- **Approvals only, and "finalized".** I treat the county records as approvals only (from the state rep). The assumption that they are finalized, with no pending appeal, is unverified, so the site never calls them "final". Their appeal outcome reads "Not in our records". Method states the assumption openly. Please confirm with the rep.
- **Reasons on appeal point both ways.** On appeal a reason is a petitioner's assignment of error, so it argues the petitioner's side, which can be for or against the project. Each one shows "Raised by petitioner" and LUBA's ruling (agreed, did not agree, did not reach). Without that, a category such as "Farmland loss" could be misread as a reason to approve. Whether to also show the petitioner's side (applicant or neighbor) on every reason is your call; I show it once per appeal.
- **Quotes are undecided, so the design works both ways.** Each reason can carry a direct quote from the document. The case view has a quotes-shown and a quotes-hidden variant (category, provenance and a page reference remain). Build quotes as removable elements behind one site setting.
- **Several reasons per approval is unknown.** The counts are of reasons, not approvals, and the copy says a decision "can have several reasons, or none we could extract". If it turns out to be exactly one, reword and the chart equals approvals.
- **Overlap with the approvals.** The three appeal examples are two county denials and one conditional approval. If that conditional approval is finalized it is probably among the ~200. I kept the two sources separate, added a cross-link on that item and a note, and counted nothing twice. Please decide whether the cross-link stays.
- **Hand-checked vs machine-extracted for ~200 PDFs.** I expect most to be machine-extracted. The chips and the per-panel counts keep that visible. Reasons come from a locally run extraction pipeline, each with a direct quote. The placeholder split (46 hand-checked, 331 machine-extracted) is invented.
- **Appeal outcome vocabulary.** I used Affirmed, Reversed, Remanded, Dismissed and "Not in our records". Please confirm the values in your data.
- **Placeholder values.** The "approvals loaded" state (200 approvals, county spread, reason counts) and the names of the three appeal examples are invented to show layout. Replace them with your data.
- **County geometry.** The mockup map uses Census generalized county shapes so I could draw something now. Replace with the BLM boundaries from your repo. If those are much more detailed, simplify them to about 2 to 4 pixels at the largest display size.
- **LUBA explainer facts.** "Usually within 21 days" and the three outcomes (affirm, reverse, remand) are from my general knowledge of Oregon law. Verify against LUBA's own pages before launch.
- **Contrast of count-ramp neighbours.** Adjacent classes are 1.2:1 to 2.5:1 apart by design (they are ordered by lightness). I rely on printed counts and the table instead. If you want a strict reading of WCAG 1.4.11, add a thin ink outline per class.
- **Yellow on light pages.** The synthetic banner's yellow is 1.3:1 against the light page, but its black stripes and 6px black borders are 16:1, so the banner reads clearly. Worth a quick user test.
- **Okabe and Ito instead of ColorBrewer qualitative.** No ColorBrewer qualitative set is colour-blind safe at eight classes, so I used Okabe and Ito with a neutral for Other.
- **Screen reader testing.** Not done. The markup follows the patterns above but should be tested with NVDA and VoiceOver.
