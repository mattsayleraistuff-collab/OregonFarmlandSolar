# Build brief for the static site

Build plain HTML, CSS and vanilla JavaScript. No framework, no build step required, no third-party requests (no CDN, fonts, analytics or map tiles).

## Files

```
index.html            one page, six regions (#overview #map #reasons #appeal-examples #appeals #method), each also a standalone page region
css/site-tokens.css   from assets/Handoff/site-tokens.css
css/site.css          from assets/Handoff/site.css (put class "ofs-page" on <body>)
js/app.js             data mode, source type, map, chart, county panel
data/                 the project repo's data (JSON/CSV), plus synthetic.json (invented)
data/oregon-counties.geojson   BLM boundaries, generalized
```

## Tokens

Use `site-tokens.css` as is. `tokens.dtcg.json` is the same set in the W3C Design Tokens format (light in `$value`, dark in `$extensions.mode.dark`). Do not hard-code colours.

## Behaviours

- **Data mode.** `?data=real` (default) or `?data=synthetic`. Read it on load; write it on change with `history.replaceState`. When synthetic: render the banner, set `document.title = "[Synthetic demo data] " + title`, add `.is-synthetic-frame` and the tag to every panel that shows data, and announce the change in an `aria-live="polite"` region. Load `data/synthetic.json` only in this mode, and never mix the two.
- **Data states.** Three: `loaded` (county approvals present), `pending` (approvals file missing or empty: show the "not loaded yet" notice, a hatched map, dashes in tables, no chart) and `synthetic`. Decide `pending` when `data/county-approvals.json` is absent or has 0 rows. The LUBA examples work in all three states.
- **Source types.** County records and LUBA appeal examples are separate panels with separate numbers. Never add them. The map and county table use county records only.
- **Map.** Build one `<svg viewBox>` from the GeoJSON at load (project with a conic conformal or Oregon Lambert projection, `fitExtent` equivalent in JS or pre-project offline). Each county is `<a href="#county-<slug>" aria-label="<Name> County: N cases in our records">` around a `<path class="ofs-county cK">`. Class `cK`: 0 none, 1, 2, 3–4 → 3, 5–9 → 4, 10+ → 5. County with 0 uses a hatch pattern fill. Selected county: class `is-selected` and `aria-current="true"`. Labels per `ofs-maplabel`.
- **Map keyboard.** One tab stop for the map group. Arrow keys move to the nearest county in that direction (use centroids), Enter or Space selects, Escape moves focus to the county select. Selecting updates `#county-detail`, the select, the table row (`aria-selected`) and the hash, and sets `aria-live="polite"` on the panel.
- **Legend** is fixed to the classes above. Do not rescale it to the data.
- **Reasons chart.** County records: one series (reasons given by the county), bars on a shared scale, no appeal column (appeals are not tracked). LUBA appeal examples: one glyph mark per reason, solid for the county and hatched for the appeal. Counts come from the data; rows with 0 stay visible. Always render the table view too.
- **Empty states.** Zero approvals in a county (data loaded): the empty-county notice. No approvals loaded at all: the pending notice. Always show the "Only 3 appeal examples" notice with the appeal examples.
- **Appeal examples.** A list of the three LUBA cases (title, county, county outcome, appeal outcome where in our records). Opening one shows its proceedings in order: county decision (an approval), then the appeal. Each reason: category, provenance chip, quotes with source and page number. End with the "end of proceedings in our records" line.
- **Nav.** Under 860px the nav collapses into a Menu button (`aria-expanded`, `aria-controls`); no JavaScript-dependent content otherwise.
- **Theme.** CSS follows `prefers-color-scheme`. If you add a toggle, store it in `localStorage` inside try/catch and set `data-theme` on `<html>`.
- **Print.** Hide nav and switches, keep banner, notices, map, legend and tables.

## Data contract (suggested, adapt to the repo)

```json
{ "cases": [ { "id": "", "project": "", "county": "Umatilla", "source_type": "county|luba",
    "proceedings": [ { "order": 1, "kind": "county_decision|luba_appeal", "outcome": "approved|conditional|denied|affirmed|reversed|remanded|dismissed",
      "reasons": [ { "category": 1, "provenance": "hand|machine", "raised_by": "county|petitioner", "petitioner_position": "seeks_approval|seeks_denial", "ruling": "sustained|denied|not_reached", "quotes": [ { "text": "", "source": "", "page": 14 } ] } ] } ] } ] }
```

Category numbers 1 to 8 match `cat-1` to `cat-8` and the eight names in the README.

## Quotes

Quotes may or may not ship. Render each quote as its own element and read one flag (`SHOW_QUOTES` in `js/config.js`). When false, show the category, provenance chip and "Source: <document>, page N" only. Do not load quote text at all when the flag is off.

## Appeal reasons

On a LUBA proceeding a reason is an assignment of error. `raised_by` is `petitioner`, `ruling` says what LUBA decided. Show the "Raised by petitioner" chip and the ruling chip with each. `reasons` on the county decision have `raised_by: county` and no ruling.

## Do not

Show "final" anywhere. Add county and LUBA numbers. Show 0 where data is not loaded or not tracked. Draw the LUBA examples on the county map. Hide counties with zero approvals. Use colour alone for meaning. Remove focus outlines. Load anything from another origin.
