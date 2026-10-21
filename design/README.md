Oregon Farmland Solar is a civic data tool: calm, credible, plain-spoken. It shows the reasons Oregon counties gave when they approved solar projects on farmland, and three LUBA appeal cases that show how an appeal works. It is not marketing. Build it as a static site in plain HTML, CSS and vanilla JavaScript. Read `handoff.md` for the build brief, `accessibility.md` for decisions and open questions, and `contrast.md` for every contrast ratio.

All numbers, counties, projects and quotes in the screens are **placeholders**. Real data comes from the project's own sources and is not part of this system: a state-provided spreadsheet and about 200 county approval PDFs (approvals only), and three LUBA opinions held separately. The approvals may not arrive before the first demo, so every screen has a "not loaded yet" state.

## Content fundamentals

- Say what the data is. County records are **approvals only**: denied projects are not in the records, so never imply anything about why projects are denied or how often. We have not checked which approvals were appealed.
- The three LUBA cases are **appeal examples**, not a sample of the approvals. Keep them in their own panels, never in county totals or on the county map.
- "No data yet" and "none" are different. While approvals are missing say "County approvals have not been loaded yet" and hatch the map; once loaded, say "No approvals in our records for X County".
- Write for someone who has never read a land use decision. Short sentences, everyday words, no acronyms on first use ("Land Use Board of Appeals (LUBA)").
- Say what the data is and is not. Never imply a statewide survey. About the appeal examples, say "Only 3 appeal examples."
- Use these labels exactly: **county outcome**, **appeal outcome (where in our records)**, **hand-checked**, **machine-extracted**, **Real records**, **Synthetic demo data**, **County records**, **LUBA appeal examples**. Never write "final".
- Say "reasons given", not "reasons". Quote sources, with page numbers: "Findings of fact, county records, page 14".
- County records and LUBA cases are different source types. Report them separately, in separate numbers, tabs or panels. Never add them.
- Zero is a result, not an error: "No cases in our records for Wheeler County. That does not mean there are no solar projects here."
- Sentence case, no exclamation marks, no emoji, no persuasion.

## Visual foundations

**Ground.** Warm neutral `bg` with white `surface` cards in light; `bg` near-black blue with `surface` one step lighter in dark. Set text in `ink`; secondary text in `ink-muted`. Use `sunken` for recessed things (table headers, empty states, counties with no cases).

**Colour with a job.** Blue (`accent`) means "you can act here" (links, primary button, selected). Blue also appears in the count ramp, which only ever appears on the map, legend and its table. Orange (`focus`) means "you are here" (keyboard focus) and nothing else. Yellow `synth-bg` means "this data is invented" and nothing else.

**Two palettes, never mixed.**

1. **Sequential (counts, map):** ColorBrewer Blues, five classes: no cases (hatched), 1, 2, 3–4, 5–9, 10 or more. In dark theme the ramp runs dark to light so more cases are always brighter against the page. Put each class's number on the county when the county is large enough (`seq-n-ink` on `seq-n`).
2. **Qualitative (eight reason categories):** Okabe and Ito colour-blind-safe set, with a neutral for "Other (uncoded)". Every mark has a `cat-outline` edge, a glyph shape (circle, square, triangle, diamond, inverted triangle, hexagon, plus, ring), the category name in text, and its count in text.

**Meaning beyond colour.** Outcomes: icon + word (check Approved, check Approved with conditions, x Denied; the county records are approvals, the appeal examples include two denials and one conditional approval; appeal outcomes use arrow and line icons; dashed circle = Not in our records). Provenance: solid border + check-box icon = hand-checked; dashed border + chip icon = machine-extracted. Reasons given by the county are solid marks; reasons given on appeal are hatched.

**Type.** System fonts only, no downloads. Headings in the serif stack (`h1`–`h3`), everything else in the sans stack. 16px body, 14px is the smallest size. Max line length `measure` (68ch).

**Spacing and shape.** 4px base, steps `space-1` to `space-8`. Flat surfaces with 1px `border` dividers; edges of controls use `border-strong` at 2px. Radii `radius-sm` 4, `radius-md` 8; the pill only for the data switch. No shadows, no gradients except the hazard stripes of the synthetic banner.

**Controls.** Minimum 44px tall (`tap-target`). Focus: `3px solid focus`, 2px offset, on everything. No hover-only information.

**Motion.** None needed. Only short colour transitions, removed under `prefers-reduced-motion: reduce`.

**Synthetic data.** When selected: sticky yellow banner at the top of every page, a "Synthetic demo data" tag and striped frame on every data panel, `[Synthetic demo data]` at the start of the page title, and the choice kept in the URL. No page may show synthetic data without all of these.

**Small and missing numbers.** The three appeal examples use one mark per reason. County approvals (about 200) use bars. Never rescale the legend to the data, keep empty rows and counties visible, and for county records show a "not loaded yet" panel (never zeros) until the approvals are in.

**Iconography.** Inline SVG, 20px grid, 1.75px stroke, `currentColor`, always with visible text. Icons never stand alone. No icon font, no emoji.

**Wordmark.** "Oregon Farmland Solar" in the serif stack, bold. There is no logo.

## Colour

### Base and action
| Token | Light | Dark | Use |
|---|---|---|---|
| `bg` | #F7F6F2 | #101418 | Page background. Text on it: ink, ink-muted, accent. |
| `surface` | #FFFFFF | #181E24 | Cards, tables, inputs, panels. Text on it: ink, ink-muted, accent. |
| `sunken` | #ECEAE3 | #0B0E11 | Recessed areas: table headers, empty states, map counties with no cases. Text on it: ink, ink-muted. |
| `border` | #CFCBC0 | #38414B | DECORATIVE dividers only (table rows, card edges). Never the only edge of a control: 1.5:1 / 1.8:1. |
| `border-strong` | #6F6B60 | #8794A2 | Edges of inputs, buttons, chips, map county outlines, chart axes. 4.4:1+ on bg, surface and sunken in both themes (needs 3:1). |
| `ink` | #1D1F21 | #ECEFF2 | Primary text and chart mark outlines on bg, surface, sunken, info-bg, caution-bg (13:1+). |
| `ink-muted` | #4A4F55 | #AEB7C0 | Secondary text, captions, table meta on bg, surface, sunken (6.8:1+). Not for disabled controls. |
| `accent` | #0B4F8A | #8EC1F5 | Links, primary button fill, selected states on bg and surface (7.7:1+). |
| `accent-hover` | #083B69 | #B3D6F8 | Hover and pressed fill of the primary button; hovered link text. |
| `on-accent` | #FFFFFF | #0B1B2B | Text and icons on accent fills (8.4:1 light, 9.2:1 dark). |
| `focus` | #B34700 | #FFC24D | Focus ring (3px solid, 2px offset) on bg, surface and sunken: 4.5:1+ light, 10:1+ dark. Never used for anything else. |

### Notices and outcomes
| Token | Light | Dark | Use |
|---|---|---|---|
| `info-bg` | #E3EEF9 | #12263A | Fill of the scope (info) notice. Text on it: ink. |
| `info-border` | #0B4F8A | #8EC1F5 | Border and icon of the scope (info) notice (7.7:1+ on bg). |
| `caution-bg` | #FFF1D6 | #2B2110 | Fill of the "not pooled, not final" notice. Text on it: ink. |
| `caution-border` | #8A5300 | #E0A030 | Border and icon of the caution notice (5.8:1+ on bg). |
| `synth-bg` | #FFD23F | #FFD23F | Synthetic-data banner fill, identical in both themes so it is never missed. Text on it: synth-ink (13:1+). |
| `synth-ink` | #1A1400 | #1A1400 | Text, icons and hazard stripes on synth-bg. |
| `approve-bg` | #E1EEF9 | #16314A | Fill of the "Approved" outcome chip. Text: approve-ink. |
| `approve-ink` | #0A3F6E | #D3E6F9 | Text of the "Approved" chip on approve-bg (9:1+). |
| `approve-border` | #0B4F8A | #7DB7F0 | Border of the "Approved" chip (3:1+ on bg and on approve-bg). Blue side of the blue/orange outcome pair. |
| `deny-bg` | #FBE6D8 | #3A2112 | Fill of the "Denied" outcome chip. Text: deny-ink. |
| `deny-ink` | #6E2900 | #FBD7BF | Text of the "Denied" chip on deny-bg (8.7:1+). |
| `deny-border` | #B34700 | #F09A5A | Border of the "Denied" chip (4.5:1+). Orange side of the blue/orange outcome pair, safe for red-green colour blindness. |

### Sequential palette (counts)
| Token | Light | Dark | Use |
|---|---|---|---|
| `seq-1` | #C6DBEF | #1F4A73 | Map class 1: 1 case. Lightest in light theme, darkest in dark theme (more cases = more contrast with the page in both). |
| `seq-2` | #9ECAE1 | #2F6EA6 | Map class 2: 2 cases. |
| `seq-3` | #6BAED6 | #5B97CB | Map class 3: 3–4 cases. |
| `seq-4` | #2171B5 | #93C0E8 | Map class 4: 5–9 cases. |
| `seq-5` | #08306B | #D3E7F8 | Map class 5: 10 or more cases. |
| `seq-1-ink` | #1D1F21 | #FFFFFF | County count labels on seq-1 (11:1 light, 9.2:1 dark). |
| `seq-2-ink` | #1D1F21 | #FFFFFF | County count labels on seq-2 (9.4:1 light, 5.4:1 dark). |
| `seq-3-ink` | #1D1F21 | #0B0E11 | County count labels on seq-3 (6.8:1 light, 6.2:1 dark). |
| `seq-4-ink` | #FFFFFF | #0B0E11 | County count labels on seq-4 (5.1:1 light, 10:1 dark). |
| `seq-5-ink` | #FFFFFF | #0B0E11 | County count labels on seq-5 (12.8:1 light, 15:1 dark). |
| `map-stroke` | #6F6B60 | #8794A2 | Outline of every county (0.75px). Gives each shape a 4.9:1 / 6:1 edge against the page, so no county depends on its fill for visibility. |

### Qualitative palette (eight reason categories)
| Token | Light | Dark | Use |
|---|---|---|---|
| `cat-1` | #0072B2 | #0072B2 | Category 1: No local authority for the use. Always drawn with a cat-outline stroke and the circle glyph. |
| `cat-2` | #D55E00 | #D55E00 | Category 2: State farmland standards. Square glyph. |
| `cat-3` | #009E73 | #009E73 | Category 3: Goal exception criteria. Triangle glyph. |
| `cat-4` | #E69F00 | #E69F00 | Category 4: Neighbor farm impacts. Diamond glyph. |
| `cat-5` | #56B4E9 | #56B4E9 | Category 5: Visual and tourism impacts. Inverted-triangle glyph. |
| `cat-6` | #CC79A7 | #CC79A7 | Category 6: Farmland loss. Hexagon glyph. |
| `cat-7` | #F0E442 | #F0E442 | Category 7: Inadequate findings. Plus glyph. |
| `cat-8` | #4D4D4D | #4D4D4D | Category 8: Other (uncoded). Ring glyph. Neutral on purpose: "uncoded" is not a topic. |
| `cat-outline` | {ink} | {ink} | Stroke (1.5px) around every category mark. It carries the 3:1 edge, because cat-4, cat-5 and cat-7 fills are under 3:1 against surface. |

| Category | Token | Glyph |
|---|---|---|
| No local authority for the use | `cat-1` | circle |
| State farmland standards | `cat-2` | square |
| Goal exception criteria | `cat-3` | triangle |
| Neighbor farm impacts | `cat-4` | diamond |
| Visual and tourism impacts | `cat-5` | inverted triangle |
| Farmland loss | `cat-6` | hexagon |
| Inadequate findings | `cat-7` | plus |
| Other (uncoded) | `cat-8` | ring |

Contrast ratios for every pairing used are in `contrast.md`.

## Type scale

| Style | Size / line height | Weight | Use |
|---|---|---|---|
| `h1` (serif) | 36px / 42px | 700 | Page title, once per page. 30px / 36px under 640px container width. |
| `h2` (serif) | 28px / 34px | 700 | Region headings. |
| `h3` (serif) | 22px / 28px | 700 | Card and panel headings. |
| `lead` (sans) | 18px / 28px | 400 | Scope statement and region introductions. Max 68ch. |
| `body` (sans) | 16px / 24px | 400 | Default text. 16px is the floor for running text. |
| `label` (sans) | 14px / 20px | 600 | Field labels, chips, table headers, legend items. 14px is the smallest size on the site. |
| `small` (sans) | 14px / 20px | 400 | Captions, source lines, footnotes. |
| `stat` (sans) | 48px / 52px | 700 | The one big number on Overview and county panels. Tabular figures. |
| `code` (mono) | 14px / 20px | 400 | Case numbers and file names. |

## Spacing, radius and sizes

| Token | Value | Use |
|---|---|---|
| `space-1` | 4px | Icon-to-label gap, chip padding. |
| `space-2` | 8px | Gap inside controls and between chips. |
| `space-3` | 12px | Control padding block; list item gap. |
| `space-4` | 16px | Page gutter on phones, card padding, paragraph gap. |
| `space-5` | 24px | Card padding on desktop, gap between related blocks. |
| `space-6` | 32px | Gap between page regions on phones. |
| `space-7` | 48px | Gap between page regions on desktop. |
| `space-8` | 64px | Top and bottom padding of a page region on desktop. |
| `radius-sm` | 4px | Chips, table wrappers, notice corners. |
| `radius-md` | 8px | Buttons, selects, cards. |
| `radius-pill` | 999px | Segmented switch only. |
| `tap-target` | 44px | Minimum height of every interactive control (WCAG 2.2 asks for 24px; we use 44px). |
| `focus-width` | 3px | Focus ring thickness. |
| `focus-offset` | 2px | Gap between control and focus ring so the ring always sits on the page ground. |
| `content-max` | 1120px | Maximum width of page content. |
| `measure` | 68ch | Maximum line length for running text. |
| `mark-stroke` | 1.5px | Outline of chart marks and legend swatches. |
| `map-stroke-width` | 0.75px | County outline weight (3px for the selected county). |

## Components

Each has a live preview with its states. Use the tokens, never raw values.

| Component | States shown |
|---|---|
| Button | default, hover, focus, pressed, disabled; primary and secondary |
| DataSwitch | Real/Synthetic; selected, unselected, focus |
| Select | default, focus, disabled |
| DataTable | caption, scope headers, numeric columns, selected row, totals row, scroll region |
| Chip | outcome (county, appeal), provenance, source type, category, synthetic tag |
| Notice | scope, not pooled and not final, small number, empty county, synthetic banner |
| MapLegend | five classes, no-data hatch, selected county |
| FocusStates | buttons, select, link, chip, county shape |
| CountyMap | 36 counties, classes 0–5, selected county, labels |
| ReasonsChart | bars for county approvals (one series); unit marks for LUBA examples (county vs appeal) |
| CaseTimeline | proceedings in order, reasons, provenance, quotes with page numbers |
| AppealExamples | list of the three LUBA cases, placeholder and synthetic variants |

## Screens

Overview, County map, Reasons, Appeal examples, Explainer and Method, each at desktop (1040px) and phone (390px) widths in light and dark, plus **DataModes**, which shows the three data states one above the other. In the screen specimens, desktop light shows real records with approvals loaded (placeholder values), phone dark shows real records with approvals not loaded yet, and desktop dark and phone light show synthetic data. The Appeal examples screen is synthetic everywhere because its quotes are invented.
