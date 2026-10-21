import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import {
  appealCases, buildMap, chartRows, classFor, countyCounts, countyProjects, dataState,
  makeProjection, nearestInDirection, outcomeView, parseMode, plural, slug, sourceLine,
} from "../../site/js/lib.js";

const geo = JSON.parse(readFileSync(new URL("../../data/geo/oregon-counties.geojson", import.meta.url)));
const site = JSON.parse(readFileSync(new URL("../../site/data/site-data.json", import.meta.url)));

test("classFor buckets counts like the legend", () => {
  const got = [0, 1, 2, 3, 4, 5, 9, 10, 40].map(classFor);
  assert.deepEqual(got, [0, 1, 2, 3, 3, 4, 4, 5, 5]);
  assert.equal(classFor(null), null);
  assert.equal(classFor(undefined), null);
});

test("parseMode only returns synthetic when asked, else real", () => {
  assert.equal(parseMode("?data=synthetic"), "synthetic");
  assert.equal(parseMode("?data=real"), "real");
  assert.equal(parseMode(""), "real");
  assert.equal(parseMode("?data=SYNTHETIC"), "real");
  assert.equal(parseMode("?data=%3Cscript%3E"), "real");
});

test("slug", () => {
  assert.equal(slug("Hood River"), "hood-river");
  assert.equal(slug("Baker"), "baker");
});

test("dataState: synthetic, pending when no county records, loaded when present", () => {
  assert.equal(dataState("synthetic", site.synthetic), "synthetic");
  assert.equal(dataState("real", site.real), "pending");
  assert.equal(dataState("real", { source_types: { county: { n_projects: 0 } } }), "pending");
  assert.equal(dataState("real", { source_types: { county: { n_projects: 5 } } }), "loaded");
  assert.equal(dataState("real", { source_types: {} }), "pending");
});

test("outcomeView never says final and handles a missing outcome", () => {
  assert.equal(outcomeView("denied").tone, "deny");
  assert.equal(outcomeView("approved_with_conditions").label, "Approved with conditions");
  assert.equal(outcomeView("reversed").label, "Reversed");
  assert.equal(outcomeView(null).label, "Not in our records");
  assert.equal(outcomeView("bogus").label, "Not in our records");
  for (const k of ["approved", "denied", "affirmed", "reversed", "remanded", "dismissed"])
    assert.doesNotMatch(outcomeView(k).label, /final/i);
});

test("plural", () => {
  assert.equal(plural(1, "approval"), "1 approval");
  assert.equal(plural(0, "approval"), "0 approvals");
});

test("chartRows scales to the largest count and keeps zero rows", () => {
  const rows = chartRows(
    [{ id: "a", label: "A", local: 4 }, { id: "b", label: "B", local: 2 }, { id: "c", label: "C", local: 0 }],
    "local",
  );
  assert.deepEqual(rows.map((r) => r.pct), [100, 50, 0]);
  assert.equal(rows.length, 3);
  assert.equal(chartRows([{ id: "a", label: "A", local: 0 }], "local")[0].pct, 0);
});

test("projection puts Portland north-west of Burns and keeps north up", () => {
  const p = makeProjection();
  const [px, py] = p(-122.68, 45.52);
  const [bx, by] = p(-119.05, 43.59);
  assert.ok(px < bx);
  assert.ok(py > by); // y points up before the SVG flip
});

test("buildMap draws all 36 counties inside the box with a label point in each box", () => {
  const m = buildMap(geo, { width: 600, height: 460, pad: 6 });
  assert.equal(m.length, 36);
  assert.equal(new Set(m.map((c) => c.fips)).size, 36);
  assert.equal(new Set(m.map((c) => c.slug)).size, 36);
  for (const c of m) {
    assert.match(c.d, /^M[-\d.,LMZ]+$/);
    assert.ok(c.cx > 0 && c.cx < 600 && c.cy > 0 && c.cy < 460, c.name);
  }
  const by = Object.fromEntries(m.map((c) => [c.name, c]));
  assert.ok(by.Multnomah.cy < by.Klamath.cy); // north is up
  assert.ok(by.Lincoln.cx < by.Malheur.cx); // west is left
});

test("nearestInDirection moves to the neighbour in that direction", () => {
  const m = buildMap(geo);
  const by = Object.fromEntries(m.map((c) => [c.name, c]));
  assert.equal(nearestInDirection(by.Wasco, m, "right") !== null, true);
  assert.ok(nearestInDirection(by.Wasco, m, "right").cx > by.Wasco.cx);
  assert.ok(nearestInDirection(by.Wasco, m, "down").cy > by.Wasco.cy);
  assert.ok(nearestInDirection(by.Wasco, m, "up").cy < by.Wasco.cy);
  assert.ok(nearestInDirection(by.Wasco, m, "left").cx < by.Wasco.cx);
  assert.equal(nearestInDirection(by.Wasco, m, "diagonal"), null);
});

test("nearestInDirection returns null at the edge", () => {
  const items = [{ cx: 0, cy: 0 }, { cx: 10, cy: 0 }];
  assert.equal(nearestInDirection(items[1], items, "right"), null);
  assert.equal(nearestInDirection(items[0], items, "right"), items[1]);
});

test("every real navigation step reaches a county (no dead ends in the middle of the state)", () => {
  const m = buildMap(geo);
  const by = Object.fromEntries(m.map((c) => [c.name, c]));
  for (const dir of ["left", "right", "up", "down"])
    assert.ok(nearestInDirection(by.Deschutes, m, dir), dir);
});

test("countyCounts is null until county records exist, then keyed by FIPS", () => {
  assert.equal(countyCounts(site.real), null);
  const c = countyCounts(site.synthetic);
  assert.equal(Object.values(c).reduce((a, b) => a + b, 0), site.synthetic.source_types.county.n_projects);
});

test("countyProjects returns only county-record projects in that county", () => {
  const fips = Object.keys(site.synthetic.source_types.county.by_county)[0];
  const rows = countyProjects(site.synthetic, fips);
  assert.ok(rows.length > 0);
  assert.ok(rows.every((p) => p.fips === fips && p.source_type === "county"));
});

test("appealCases lists the real LUBA cases and none for synthetic data", () => {
  assert.equal(appealCases(site.real).length, 3);
  assert.equal(appealCases(site.synthetic).length, 0);
});

test("sourceLine names the document type and the PDF page", () => {
  const c = appealCases(site.real)[0];
  const r = c.proceedings.flatMap((p) => p.reasons)[0];
  assert.match(sourceLine(c.documents, r), new RegExp(`page ${r.pdf_page}$`));
  assert.match(sourceLine(c.documents, r), /^(LUBA opinion|Staff report|County decision)/);
});
