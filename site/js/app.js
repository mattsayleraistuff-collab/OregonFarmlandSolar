// Oregon Farmland Solar: draws the page from two data files (relative paths, same origin).
// Text from data is always set with textContent, never innerHTML, so data cannot inject markup.
import { SHOW_LUBA_CHART, SHOW_QUOTES } from "./config.js";
import {
  appealCases, buildMap, categoriesInUse, chartRows, classFor, countyCounts, countyProjects, dataState,
  docLabel, nearestInDirection, outcomeView, parseMode, plural, sourceLine,
} from "./lib.js";

const SVG_NS = "http://www.w3.org/2000/svg";
const $ = (id) => document.getElementById(id);

// ---- tiny DOM helpers ----------------------------------------------------------------------

function h(tag, attrs = {}, ...kids) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === false || v === null || v === undefined) continue;
    if (k === "class") node.className = v;
    else node.setAttribute(k, v === true ? "" : v);
  }
  add(node, kids);
  return node;
}

function add(node, kids) {
  for (const k of kids.flat()) {
    if (k === null || k === undefined || k === false) continue;
    node.append(k instanceof Node ? k : document.createTextNode(String(k)));
  }
}

function s(tag, attrs = {}, ...kids) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v !== null && v !== undefined) node.setAttribute(k, v);
  add(node, kids);
  return node;
}

const ICONS = {
  check: ["M4 10.5l4 4 8-9"],
  x: ["M5 5l10 10M15 5L5 15"],
  warn: ["M10 2.5l8 14H2z", "M10 8v4M10 14.5v.01"],
  info: ["M10 9v5M10 6v.01"],
  hand: ["M3.5 3.5h13v13h-13z", "M6.5 10l2.5 2.5 4.5-5"],
  machine: ["M5 5h10v10H5z", "M8 2v3M12 2v3M8 15v3M12 15v3M2 8h3M2 12h3M15 8h3M15 12h3"],
  synth: ["M10 2.5l8 14H2z", "M10 8v4M10 14.5v.01"],
  none: ["M10 3a7 7 0 1 0 0 14a7 7 0 1 0 0-14z"],
  back: ["M8 5L3 10l5 5", "M3 10h9a5 5 0 0 1 0 8"],
  swap: ["M4 7h11l-3-3", "M16 13H5l3 3"],
  minus: ["M5 10h10"],
  equals: ["M4 7h12M4 13h12"],
};
const OUTCOME_ICON = {
  approved: "check", approved_with_conditions: "check", denied: "x",
  affirmed: "equals", reversed: "swap", remanded: "back", dismissed: "minus",
};

function icon(name, size = 18) {
  const svg = s("svg", {
    class: "ofs-icon", width: size, height: size, viewBox: "0 0 20 20", fill: "none",
    stroke: "currentColor", "stroke-width": "1.75", "stroke-linecap": "round",
    "stroke-linejoin": "round", "aria-hidden": "true", focusable: "false",
  });
  for (const d of ICONS[name] ?? []) svg.append(s("path", { d }));
  if (name === "none") svg.firstChild.setAttribute("stroke-dasharray", "3 3");
  return svg;
}

const GLYPHS = [
  (a) => s("circle", { ...a, cx: 10, cy: 10, r: 7.25 }),
  (a) => s("rect", { ...a, x: 3.25, y: 3.25, width: 13.5, height: 13.5 }),
  (a) => s("path", { ...a, d: "M10 3L17.5 16.5h-15z" }),
  (a) => s("path", { ...a, d: "M10 2L18 10 10 18 2 10z" }),
  (a) => s("path", { ...a, d: "M2.5 3.5h15L10 17z" }),
  (a) => s("path", { ...a, d: "M5.5 3h9L19 10l-4.5 7h-9L1 10z" }),
  (a) => s("path", { ...a, d: "M7 2.5h6v4.5h4.5v6H13v4.5H7V13H2.5V7H7z" }),
  (a) => s("path", { ...a, "fill-rule": "evenodd", d: "M10 2.75a7.25 7.25 0 1 0 0 14.5a7.25 7.25 0 1 0 0-14.5zM10 6.5a3.5 3.5 0 1 1 0 7a3.5 3.5 0 1 1 0-7z" }),
];

/** Category mark: n is 1-based (cat-1 to cat-8); hatched marks are reasons given on appeal. */
function glyph(n, { hatched = false, size = 20 } = {}) {
  const fill = hatched ? `url(#hatch-${n})` : `var(--cat-${n})`;
  const svg = s("svg", { class: "ofs-glyph", width: size, height: size, viewBox: "0 0 20 20", "aria-hidden": "true", focusable: "false" });
  const g = s("g", { class: "cat-mark", style: `fill:${fill};stroke:var(--cat-outline);stroke-width:1.5;stroke-linejoin:round` });
  g.append(GLYPHS[n - 1]({}));
  svg.append(g);
  return svg;
}

function defs() {
  const d = s("defs");
  for (let n = 1; n <= 8; n++) {
    const p = s("pattern", { id: `hatch-${n}`, width: 5, height: 5, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" });
    p.append(s("rect", { width: 5, height: 5, style: "fill:var(--surface)" }), s("rect", { width: 2.5, height: 5, style: `fill:var(--cat-${n})` }));
    d.append(p);
  }
  const none = s("pattern", { id: "none", width: 6, height: 6, patternUnits: "userSpaceOnUse", patternTransform: "rotate(-45)" });
  none.append(s("rect", { width: 6, height: 6, style: "fill:var(--sunken)" }), s("rect", { width: 1.5, height: 6, style: "fill:var(--map-stroke);opacity:.55" }));
  d.append(none);
  return d;
}

// ---- small components ---------------------------------------------------------------------

const chip = (cls, iconName, text) => h("span", { class: `ofs-chip ${cls}` }, iconName ? icon(iconName, 16) : null, text);
const synthChip = () => chip("is-synth", "synth", "Synthetic demo data");
const handChip = () => chip("is-hand", "hand", "hand-checked");
const machineChip = () => chip("is-machine", "machine", "machine-extracted");
const sourceChip = (text) => h("span", { class: "ofs-chip is-source" }, text);

function outcomeChip(value) {
  const v = outcomeView(value);
  const ic = value ? (OUTCOME_ICON[value] ?? "none") : "none";
  return chip(`is-${v.tone}`, ic, v.label);
}

function outcomes(rows) {
  return h("dl", { class: "ofs-outcomes" }, rows.map(([term, value]) => h("div", {}, h("dt", {}, term), h("dd", {}, value))));
}

function notice(kind, iconName, ...paras) {
  return h("div", { class: `ofs-notice is-${kind}`, role: "note" }, icon(iconName, 24), h("div", {}, paras.map((p) => h("p", {}, p))));
}

function tablewrap(label, table, extra = {}) {
  return h("div", { class: "ofs-tablewrap", tabindex: "0", role: "region", "aria-label": label, ...extra }, table);
}

function details(summary, body) {
  return h("details", { class: "ofs-details", open: true }, h("summary", {}, icon("check", 18), summary), body);
}

// ---- state ---------------------------------------------------------------------------------

const state = { mode: "real", site: null, geo: null, map: [], selected: null, caseId: null };
const section = () => state.site[state.mode];

// ---- rendering -----------------------------------------------------------------------------

function renderChrome() {
  const synthetic = state.mode === "synthetic";
  document.title = (synthetic ? "[Synthetic demo data] " : "") + "Oregon Farmland Solar";
  $("d-real").checked = !synthetic;
  $("d-syn").checked = synthetic;
  const banner = $("synth-banner");
  banner.hidden = !synthetic;
  banner.replaceChildren();
  if (synthetic) {
    banner.className = "ofs-synth";
    banner.setAttribute("role", "status");
    const btn = h("button", { class: "ofs-btn is-small", type: "button" }, "Switch to real records");
    btn.addEventListener("click", () => setMode("real"));
    banner.append(h("div", { class: "ofs-wrap" }, icon("synth", 32), h("div", {}, h("strong", {}, "Synthetic demo data is showing"), h("p", {}, "Everything on this page is invented. Do not read any number, county, project, quote or outcome as a finding about real places or decisions.")), btn));
  }
  const st = dataState(state.mode, section());
  $("mode-note").textContent =
    st === "synthetic" ? "Showing invented data for demonstration. The address bar says ?data=synthetic."
      : st === "pending" ? "Showing real records. County approvals are not loaded yet."
        : "Showing real records: county approvals and LUBA appeal examples.";
  const pending = st === "pending";
  for (const id of ["county-load-note", "scope-county-note"]) $(id).hidden = !pending;
}

function frame(node) {
  if (state.mode !== "synthetic") return node;
  node.classList.add("is-synthetic-frame");
  node.prepend(h("p", { style: "margin:0 0 var(--space-2)" }, synthChip()));
  return node;
}

function renderOverview() {
  const sec = section();
  const st = dataState(state.mode, sec);
  const county = sec.source_types.county;
  const cases = appealCases(sec);
  const tag = state.mode === "synthetic" ? h("p", { class: "ofs-small", style: "margin:0" }, synthChip()) : null;
  const countyCard = h("div", { class: "ofs-card" },
    h("p", { class: "ofs-small", style: "margin:0" }, "County records (approvals only)"),
    h("p", { style: "margin:0" }, h("span", { class: "ofs-stat" }, st === "pending" ? "—" : county.n_projects), " ", h("span", { class: "ofs-lead" }, st === "pending" ? "not loaded yet" : "approvals")),
    tag ?? h("p", { class: "ofs-small", style: "margin:0" }, "Approved projects from the state’s list"));
  const lubaCard = h("div", { class: "ofs-card" },
    h("p", { class: "ofs-small", style: "margin:0" }, "LUBA appeal examples (separate)"),
    h("p", { style: "margin:0" }, h("span", { class: "ofs-stat" }, state.mode === "synthetic" ? "—" : cases.length), " ", h("span", { class: "ofs-lead" }, state.mode === "synthetic" ? "not shown with synthetic data" : "cases")),
    h("p", { class: "ofs-small", style: "margin:0" }, "Shown on their own to explain appeals"));
  const out = [h("div", { class: "ofs-cols is-two", style: "gap:var(--space-4)" }, countyCard, lubaCard)];
  if (st === "pending")
    out.push(notice("empty", "info", [h("strong", {}, "County approvals have not been loaded yet."), " The hatching on the map means “no data yet”, not “no projects”. The appeal examples are available now."], [h("a", { href: "#appeal-examples" }, "Go to the appeal examples")]));
  $("overview-dyn").replaceChildren(...out);
}

// ---- map ----------------------------------------------------------------------------------

function renderMap() {
  const sec = section();
  const st = dataState(state.mode, sec);
  const counts = countyCounts(sec);
  const loaded = counts !== null;
  const nameOf = (c) => `${c.name} County`;
  const label = (c) => {
    if (!loaded) return `${nameOf(c)}: approvals not loaded yet`;
    const n = counts[c.fips] ?? 0;
    return `${nameOf(c)}: ${plural(n, "approval")} in our records`;
  };

  const svg = s("svg", { class: "ofs-map", id: "county-map", viewBox: "0 0 600 460", role: "group", "aria-label": loaded ? "Map of Oregon’s 36 counties, shaded by number of approved projects in our records. Counties are links. A table of the same counts follows." : "Map of Oregon’s 36 counties. County approvals are not loaded yet, so every county is hatched. Counties are links. A table follows." });
  const first = state.selected ?? state.map[0].fips;
  for (const c of state.map) {
    const n = loaded ? (counts[c.fips] ?? 0) : null;
    const cls = classFor(n);
    const a = s("a", { href: `#county-${c.slug}`, "aria-label": label(c), "data-fips": c.fips, tabindex: c.fips === first ? "0" : "-1" });
    if (c.fips === state.selected) a.setAttribute("aria-current", "true");
    const path = s("path", { class: `ofs-county c${cls ?? 0}${c.fips === state.selected ? " is-selected" : ""}`, d: c.d });
    if (!cls) path.setAttribute("style", "fill:url(#none)");
    a.append(path);
    if (cls) a.append(s("text", { class: `ofs-maplabel l${cls}`, x: c.cx, y: c.cy, "aria-hidden": "true" }, n));
    svg.append(a);
  }
  svg.addEventListener("click", (e) => {
    const a = e.target.closest("a[data-fips]");
    if (!a) return;
    e.preventDefault();
    selectCounty(a.dataset.fips, { focus: true });
  });
  svg.addEventListener("keydown", onMapKey);

  const legend = h("ul", { class: "ofs-legend", "aria-label": "Map legend: approvals in our records" },
    [["c0", "No approvals in our records"], ["c1", "1"], ["c2", "2"], ["c3", "3–4"], ["c4", "5–9"], ["c5", "10 or more"], ["sel", "Selected county"]].map(([c, t]) => h("li", {}, h("span", { class: `ofs-swatch ${c}` }), t)));

  const zero = loaded ? state.map.filter((c) => !(counts[c.fips] > 0)).length : null;
  const mapCard = frame(h("div", { class: "ofs-card ofs-mapbox" },
    h("h3", { style: "margin-bottom:var(--space-2)" }, "Approved projects per county"), svg, legend,
    h("p", { class: "ofs-small ofs-mapnote" }, "Source: county records (approvals only). LUBA appeal examples are not included here. Shapes are BLM county boundaries, generalized for display, not legal boundaries.")));

  const sel = h("select", { class: "ofs-select", id: "county-sel" }, h("option", { value: "" }, "Choose a county…"), state.map.map((c) => h("option", { value: c.fips }, c.name)));
  sel.value = state.selected ?? "";
  sel.addEventListener("change", () => (sel.value ? selectCounty(sel.value) : null));
  const side = h("div", { class: "ofs-stack" },
    h("div", { class: "ofs-field" }, h("label", { for: "county-sel" }, "Choose a county"), h("span", { class: "ofs-selectwrap" }, sel), h("span", { class: "ofs-hint" }, "Same as selecting it on the map.")),
    h("div", { class: "ofs-card", id: "county-detail", "aria-live": "polite" }));

  const total = loaded ? Object.values(counts).reduce((a, b) => a + b, 0) : null;
  const table = h("table", { class: "ofs-table" },
    h("caption", {}, loaded ? `Approvals per county — county records (${total} total; LUBA appeal examples are not included)` : "Approvals per county — county records not loaded yet"),
    h("thead", {}, h("tr", {}, h("th", { scope: "col" }, "County"), h("th", { scope: "col", class: "num" }, "Approvals"))),
    h("tbody", {}, state.map.map((c) => h("tr", { "data-fips": c.fips, "aria-selected": c.fips === state.selected ? "true" : null }, h("th", { scope: "row" }, h("a", { href: `#county-${c.slug}`, "data-fips": c.fips }, c.name)), h("td", { class: "num" }, loaded ? (counts[c.fips] ?? 0) : "—")))));
  table.addEventListener("click", (e) => {
    const a = e.target.closest("a[data-fips]");
    if (!a) return;
    e.preventDefault();
    selectCounty(a.dataset.fips, { reveal: true });
  });

  $("map-dyn").replaceChildren(
    h("div", { class: "ofs-cols is-map" }, h("div", {}, mapCard, loaded ? h("p", { class: "ofs-small", style: "margin-top:var(--space-3)" }, `${zero} of 36 counties have no approvals in our records. That says nothing about whether solar projects exist there.`) : notice("empty", "info", [h("strong", {}, "County approvals have not been loaded yet."), " Hatched counties mean “no data yet”, not “no projects”."])), side),
    details("Table of the same counts", tablewrap("Approvals per county, scrollable", table, { style: "max-height:340px;overflow:auto" })));
  renderCountyDetail();
}

function renderCountyDetail() {
  const box = $("county-detail");
  if (!box) return;
  const sec = section();
  const c = state.map.find((m) => m.fips === state.selected);
  if (!c) {
    box.replaceChildren(h("p", { class: "ofs-small", style: "margin:0" }, "Select a county on the map or from the list to see its records."));
    return;
  }
  const counts = countyCounts(sec);
  const kids = [h("h3", { tabindex: "-1" }, `${c.name} County`)];
  if (counts === null) {
    kids.push(h("p", { style: "margin:0 0 var(--space-3)" }, h("span", { class: "ofs-stat" }, "—"), " ", h("span", { class: "ofs-lead" }, "not loaded yet")), h("p", { class: "ofs-small" }, "County approvals have not been loaded yet. That does not mean there are no solar projects in this county."));
  } else {
    const rows = countyProjects(sec, c.fips);
    kids.push(h("p", { style: "margin:0 0 var(--space-3)" }, h("span", { class: "ofs-stat" }, rows.length), " ", h("span", { class: "ofs-lead" }, rows.length === 1 ? "approval in county records" : "approvals in county records")));
    if (rows.length === 0) {
      kids.push(notice("empty", "info", [h("strong", {}, `No approvals in our records for ${c.name} County.`), " That does not mean there are no solar projects here."]));
    } else {
      const shown = rows.slice(0, 3);
      kids.push(h("p", { class: "ofs-small" }, `Showing ${shown.length} of ${rows.length}. Appeals are not tracked for these records. LUBA appeal examples are listed `, h("a", { href: "#appeal-examples" }, "separately"), "."),
        h("ul", { class: "ofs-caselist" }, shown.map((p) => h("li", {},
          h("h4", {}, p.name),
          h("p", { class: "ofs-small", style: "margin:0 0 var(--space-2)" }, h("span", { class: "ofs-mono" }, p.id), " · ", plural(p.reason_count, "reason")),
          outcomes([["County outcome", outcomeChip(p.county_outcome)], ["Appeal outcome (where in our records)", outcomeChip(null)]]),
          state.mode === "synthetic" ? h("div", { class: "ofs-chips", style: "margin-top:var(--space-2)" }, synthChip()) : null))));
    }
  }
  const here = appealCases(sec).filter((k) => k.project.fips === c.fips);
  if (here.length)
    kids.push(h("p", { class: "ofs-small" }, `An appeal example from ${c.name} County is listed separately: `, here.map((k, i) => [i ? ", " : "", h("a", { href: `#case-${k.project.id}`, "data-case": k.project.id }, k.project.name)])));
  box.replaceChildren(...kids);
  box.querySelectorAll("a[data-case]").forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); openCase(a.dataset.case, { scroll: true }); }));
}

function selectCounty(fips, { focus = false, reveal = false } = {}) {
  state.selected = fips;
  const c = state.map.find((m) => m.fips === fips);
  history.replaceState(null, "", `${location.pathname}${location.search}#county-${c.slug}`);
  for (const a of document.querySelectorAll("#county-map a[data-fips]")) {
    const on = a.dataset.fips === fips;
    a.setAttribute("tabindex", on ? "0" : "-1");
    if (on) a.setAttribute("aria-current", "true"); else a.removeAttribute("aria-current");
    a.firstChild.classList.toggle("is-selected", on);
    if (on && focus) a.focus();
  }
  document.querySelectorAll("#map-dyn tr[data-fips]").forEach((tr) => (tr.getAttribute("data-fips") === fips ? tr.setAttribute("aria-selected", "true") : tr.removeAttribute("aria-selected")));
  const sel = $("county-sel");
  if (sel) sel.value = fips;
  renderCountyDetail();
  if (reveal) {
    // From the table the card can be off screen: scroll it into view and move focus to its
    // heading so keyboard and screen reader users land on the new content too.
    const box = $("county-detail");
    box.scrollIntoView({ block: "nearest" });
    box.querySelector("h3")?.focus({ preventScroll: true });
  }
}

function onMapKey(e) {
  const a = e.target.closest?.("a[data-fips]");
  if (!a) return;
  const dir = { ArrowLeft: "left", ArrowRight: "right", ArrowUp: "up", ArrowDown: "down" }[e.key];
  if (dir) {
    e.preventDefault();
    const cur = state.map.find((m) => m.fips === a.dataset.fips);
    const next = nearestInDirection(cur, state.map, dir);
    if (!next) return;
    for (const x of document.querySelectorAll("#county-map a[data-fips]")) x.setAttribute("tabindex", x.dataset.fips === next.fips ? "0" : "-1");
    document.querySelector(`#county-map a[data-fips="${next.fips}"]`).focus();
  } else if (e.key === " ") {
    e.preventDefault();
    selectCounty(a.dataset.fips);
  } else if (e.key === "Escape") {
    $("county-sel")?.focus();
  }
}

// ---- reasons -------------------------------------------------------------------------------

function categoryIndex(categories, id) {
  return categories.findIndex((c) => c.id === id) + 1;
}

function chartRowEl(cat, n, body) {
  return h("li", { class: "ofs-chartrow" }, h("span", { class: "nm" }, glyph(n), cat.label), h("span", { class: "vals" }, body));
}

function provenance(block) {
  return h("div", { class: "ofs-chips", style: "margin-top:var(--space-3)" },
    block.hand_checked ? h("span", { class: "ofs-chip is-hand" }, icon("hand", 16), `${block.hand_checked} hand-checked`) : null,
    block.reasons - block.hand_checked ? h("span", { class: "ofs-chip is-machine" }, icon("machine", 16), `${block.reasons - block.hand_checked} machine-extracted`) : null,
    h("span", { class: "ofs-small" }, "reasons in this panel"));
}

function renderReasons() {
  const sec = section();
  const st = dataState(state.mode, sec);
  const out = [];

  // County records
  const county = sec.source_types.county;
  const countyPanel = h("div", { id: "r-county", class: "ofs-stack" });
  if (st === "pending") {
    countyPanel.append(notice("empty", "info", [h("strong", {}, "County approvals have not been loaded yet."), " There is no chart for county records until they are. This is not a count of zero."]));
  } else {
    const cats = categoriesInUse(county.categories, ["local"]);
    const rows = chartRows(cats, "local");
    const list = h("ul", { class: "ofs-chartrows", "aria-label": "Reasons by category" }, rows.map((r, i) => chartRowEl(r, cats[i].number, h("span", { style: "display:flex;width:100%;align-items:center;gap:8px" }, h("span", { style: "display:flex;flex:1;height:26px;min-width:0" }, r.pct > 0 ? h("span", { style: `width:${r.pct}%;background:var(--cat-${cats[i].number});border:1.5px solid var(--cat-outline);` }) : null), h("span", { class: "ofs-count", style: "min-width:9ch" }, r.count)))));
    countyPanel.append(frame(h("div", { class: "ofs-card" },
      h("h3", { style: "margin-bottom:var(--space-2)" }, "County records: reasons given for approval"),
      h("p", { class: "ofs-small", style: "margin-bottom:var(--space-3)" }, sourceChip("Source: county records"), ` ${county.n_projects} approvals. A decision can have several reasons, or none we could extract.`),
      h("p", { class: "ofs-small", style: "margin:0 0 var(--space-3)" }, "Each bar is a count of reasons the county gave when it approved a project. Reasons given on appeal are not collected for county records."),
      list, provenance(county))));
    countyPanel.append(details("Table view: county records", tablewrap("Reasons by category, table view", h("table", { class: "ofs-table" },
      h("caption", {}, "Reasons by category — county records. A decision can have several reasons, or none we could extract, so reasons need not match approvals."),
      h("thead", {}, h("tr", {}, h("th", { scope: "col" }, "Category"), h("th", { scope: "col", class: "num" }, "Given by the county"))),
      h("tbody", {}, rows.map((r, i) => h("tr", {}, h("th", { scope: "row" }, r.label), h("td", { class: "num" }, r.count)))),
      h("tfoot", {}, h("tr", {}, h("th", { scope: "row" }, "All reasons"), h("td", { class: "num" }, county.reasons)))))));
  }
  out.push(countyPanel);

  // LUBA appeal examples
  const lubaPanel = h("div", { id: "r-luba", class: "ofs-stack", style: "margin-top:var(--space-6)" });
  const luba = sec.source_types.luba;
  if (state.mode === "synthetic" || !luba) {
    lubaPanel.append(notice("empty", "info", [h("strong", {}, "Appeal examples are not shown with synthetic data."), " The three appeal examples are real cases. Switch to real records to see them."]));
  } else {
    const cases = appealCases(sec);
    const denied = cases.filter((c) => c.project.county_outcome === "denied").length;
    const approved = cases.length - denied;
    lubaPanel.append(notice("empty", "info", [h("strong", {}, `Only ${cases.length} appeal examples`), `: ${denied} county denials and ${approved} county ${approved === 1 ? "approval" : "approvals"}. They show how an appeal works. They are not a sample of the approvals, and they cannot say how often approvals are appealed.`]));
    const cats = categoriesInUse(luba.categories, ["local", "appeal"]);
    const key = h("ul", { class: "ofs-keyrow", "aria-label": "Chart key" }, h("li", {}, glyph(1), h("span", {}, h("b", {}, "Solid"), " = reason given for the county decision")), h("li", {}, glyph(1, { hatched: true }), h("span", {}, h("b", {}, "Hatched"), " = reason given in the appeal decision")));
    const rows = h("ul", { class: "ofs-chartrows", "aria-label": "Reasons by category" }, cats.map((c) => chartRowEl(c, c.number, [
      h("span", { class: "grp" }, h("span", { class: "ofs-count" }, "County: ", h("b", {}, c.local)), " ", h("span", { class: "ofs-marks" }, Array.from({ length: c.local }, () => glyph(c.number)))),
      h("span", { class: "grp" }, h("span", { class: "ofs-count" }, "Appeal: ", h("b", {}, c.appeal)), " ", h("span", { class: "ofs-marks" }, Array.from({ length: c.appeal }, () => glyph(c.number, { hatched: true })))),
    ])));
    const table = tablewrap("Reasons by category, table view", h("table", { class: "ofs-table" },
      h("caption", {}, "Reasons by category — LUBA appeal examples. A decision can have several reasons, or none we could extract, so reasons need not match cases. Categories with no reasons are not listed."),
      h("thead", {}, h("tr", {}, ["Category", "Given by the county", "Given on appeal", "Reasons"].map((t, i) => h("th", { scope: "col", class: i ? "num" : null }, t)))),
      h("tbody", {}, cats.map((c) => h("tr", {}, h("th", { scope: "row" }, c.label), h("td", { class: "num" }, c.local), h("td", { class: "num" }, c.appeal), h("td", { class: "num" }, c.count)))),
      h("tfoot", {}, h("tr", {}, h("th", { scope: "row" }, "All reasons"), h("td", { class: "num" }, cats.reduce((a, c) => a + c.local, 0)), h("td", { class: "num" }, cats.reduce((a, c) => a + c.appeal, 0)), h("td", { class: "num" }, luba.reasons)))));
    lubaPanel.append(h("div", { class: "ofs-card" },
      h("h3", { style: "margin-bottom:var(--space-2)" }, "LUBA appeal examples: county and appeal reasons"),
      h("p", { class: "ofs-small", style: "margin-bottom:var(--space-3)" }, sourceChip("Source: LUBA case"), ` ${cases.length} cases, counted separately from the approvals above. Reasons are coded from the opinions: grounds the county gave (as LUBA recorded them) and grounds LUBA gave.`),
      ...(SHOW_LUBA_CHART ? [key, rows] : [table]), provenance(luba)));
    if (SHOW_LUBA_CHART) lubaPanel.append(details("Table view: LUBA appeal examples", table));
  }
  out.push(lubaPanel);
  $("reasons-dyn").replaceChildren(...out);
}

// ---- appeal examples -----------------------------------------------------------------------

function renderCases() {
  const sec = section();
  const box = $("cases-dyn");
  if (state.mode === "synthetic") {
    box.replaceChildren(notice("empty", "info", [h("strong", {}, "Appeal examples are not shown with synthetic data."), " The appeal examples are real LUBA cases. Switch to real records to read them."]));
    return;
  }
  const cases = appealCases(sec);
  if (!cases.length) {
    box.replaceChildren(notice("empty", "info", [h("strong", {}, "No appeal examples loaded.")]));
    return;
  }
  const list = h("ul", { class: "ofs-caselist" }, cases.map((c) => h("li", {},
    h("h4", {}, c.project.name),
    h("p", { class: "ofs-small", style: "margin:0 0 var(--space-2)" }, `${c.project.county} County · ${plural(c.proceedings.length, "proceeding")} in our records`),
    h("div", { class: "ofs-chips", style: "margin-bottom:var(--space-2)" }, sourceChip("Source: LUBA case")),
    outcomes([["County outcome", outcomeChip(c.project.county_outcome)], ["Appeal outcome (where in our records)", outcomeChip(c.project.appeal_outcome)]]),
    h("p", { style: "margin:var(--space-3) 0 0" }, h("a", { href: `#case-${c.project.id}`, "data-case": c.project.id, "aria-label": `Open this case: ${c.project.name}` }, "Open this case")))));
  list.addEventListener("click", (e) => {
    const a = e.target.closest("a[data-case]");
    if (!a) return;
    e.preventDefault();
    openCase(a.dataset.case, { scroll: true });
  });
  box.replaceChildren(list, h("div", { id: "case-view" }));
  if (!state.caseId || !cases.some((c) => c.project.id === state.caseId)) state.caseId = null;
  if (state.caseId) renderCase();
}

function openCase(id, { scroll = false } = {}) {
  state.caseId = id;
  history.replaceState(null, "", `${location.pathname}${location.search}#case-${id}`);
  renderCase();
  const view = $("case-view");
  if (view) {
    if (scroll) view.scrollIntoView();
    view.querySelector("h3")?.setAttribute("tabindex", "-1");
    view.querySelector("h3")?.focus({ preventScroll: !scroll });
  }
}

function reasonItem(categories, docs, r) {
  const n = categoryIndex(categories, r.category);
  const head = h("div", { class: "head" }, glyph(n), h("span", {}, r.label), r.hand_checked ? handChip() : machineChip());
  return h("li", {}, head, SHOW_QUOTES
    ? h("blockquote", { class: "ofs-quote" }, h("p", {}, `\u201C${r.quote}\u201D`), h("footer", {}, `${docLabel(docs, r)}, page `, h("b", {}, String(r.pdf_page))))
    : h("p", { class: "ofs-small" }, `Source: ${sourceLine(docs, r)}`));
}

function renderCase() {
  const sec = section();
  const c = appealCases(sec).find((k) => k.project.id === state.caseId);
  const view = $("case-view");
  if (!c || !view) return;
  const categories = sec.source_types.luba.categories;
  const p = c.project;
  const procs = c.proceedings.map((pr) => {
    const local = pr.level === "local";
    const when = pr.decision_date ? new Date(`${pr.decision_date}T00:00:00`).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" }) : null;
    return h("li", { class: "ofs-proc" }, h("div", { class: "ofs-card" },
      h("header", {},
        h("h3", {}, local ? "County decision" : "Appeal to the Land Use Board of Appeals"),
        h("div", { class: "ofs-chips" }, sourceChip("Source: LUBA case"), h("span", { class: "ofs-small" }, [pr.body, when, pr.citation].filter(Boolean).join(" · "))),
        outcomes([[local ? "County outcome" : "Appeal outcome (where in our records)", outcomeChip(pr.outcome)]])),
      local ? h("p", { class: "ofs-small", style: "margin:0 0 var(--space-3)" }, "The source line under each quote names the document it comes from. For these cases, the county’s reasons are usually as LUBA recorded them.") : null,
      pr.reasons.length ? h("ul", { class: "ofs-reasons" }, pr.reasons.map((r) => reasonItem(categories, c.documents, r))) : h("p", { class: "ofs-small" }, "No reasons coded for this proceeding.")));
  });
  view.replaceChildren(
    h("div", { class: "ofs-card", id: `case-${p.id}`, style: "margin-top:var(--space-5)" },
      h("h3", {}, p.name),
      h("p", { class: "ofs-small", style: "margin:0 0 var(--space-3)" }, `${p.county} County · ${plural(c.proceedings.length, "proceeding")} in our records`),
      outcomes([["County outcome", outcomeChip(p.county_outcome)], ["Appeal outcome (where in our records)", outcomeChip(p.appeal_outcome)]])),
    h("div", { style: "margin-top:var(--space-5)" }, h("ol", { class: "ofs-timeline" }, procs, h("li", { class: "ofs-end" }, "End of proceedings in our records. Later steps, such as a new county decision, may exist that we have not collected."))));
}

// ---- wiring --------------------------------------------------------------------------------

function renderAll() {
  renderChrome();
  renderOverview();
  renderMap();
  renderReasons();
  renderCases();
}

function setMode(mode) {
  if (mode === state.mode) return;
  state.mode = mode;
  state.selected = null;
  state.caseId = null;
  const url = new URL(location.href);
  url.hash = "";
  if (mode === "synthetic") url.searchParams.set("data", "synthetic"); else url.searchParams.delete("data");
  history.replaceState(null, "", url);
  renderAll();
  $("live").textContent = mode === "synthetic" ? "Now showing synthetic demo data. Everything on the page is invented." : "Now showing real records.";
}

function applyHash() {
  const m = location.hash.match(/^#(county|case)-(.+)$/);
  if (!m) return;
  if (m[1] === "county") {
    const c = state.map.find((x) => x.slug === m[2]);
    if (c) selectCounty(c.fips, { reveal: true });
  } else if (appealCases(section()).some((k) => k.project.id === m[2])) {
    openCase(m[2], { scroll: true });
  }
}

function wireChrome() {
  $("patterns").append(defs());
  for (const r of document.querySelectorAll('input[name="data"]')) r.addEventListener("change", () => r.checked && setMode(r.value));
  const header = $("site-header");
  $("menu-btn").addEventListener("click", () => {
    const open = header.classList.toggle("is-open");
    $("menu-btn").setAttribute("aria-expanded", String(open));
  });
  const nav = document.querySelectorAll("#site-nav a");
  const mark = () => {
    const id = (location.hash || "#overview").split("-")[0];
    const target = id === "#county" ? "#map" : id === "#case" ? "#appeal-examples" : id;
    nav.forEach((a) => (a.getAttribute("href") === target ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current")));
  };
  window.addEventListener("hashchange", () => { mark(); applyHash(); });
  mark();
}

async function load() {
  const [site, geo] = await Promise.all([
    fetch("data/site-data.json").then((r) => { if (!r.ok) throw new Error(`site-data.json: ${r.status}`); return r.json(); }),
    fetch("data/oregon-counties.geojson").then((r) => { if (!r.ok) throw new Error(`oregon-counties.geojson: ${r.status}`); return r.json(); }),
  ]);
  state.site = site;
  state.geo = geo;
  state.map = buildMap(geo);
  state.mode = parseMode(location.search);
  wireChrome();
  renderAll();
  applyHash();
}

load().catch((err) => {
  $("mode-note").textContent = `Could not load the data (${err.message}). Please reload the page.`;
});
