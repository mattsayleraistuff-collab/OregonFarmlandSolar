// Pure helpers for the site (no DOM, no network), so they can be tested with `node --test`.
// Everything the page shows about data goes through these functions.

export const OUTCOMES = {
  approved: { tone: "approve", label: "Approved" },
  approved_with_conditions: { tone: "approve", label: "Approved with conditions" },
  denied: { tone: "deny", label: "Denied" },
  affirmed: { tone: "neutral", label: "Affirmed" },
  reversed: { tone: "neutral", label: "Reversed" },
  remanded: { tone: "neutral", label: "Remanded" },
  dismissed: { tone: "neutral", label: "Dismissed" },
};

export const DOC_LABELS = {
  county_decision: "County decision",
  staff_report: "Staff report",
  appellate_opinion: "LUBA opinion",
  efsc_order: "Energy Facility Siting Council order",
  advocacy_comment: "Advocacy comment",
  legal_digest: "Legal digest",
  other: "Document",
};

/** Data mode from a URL query string: "synthetic" only when asked for, otherwise "real". */
export function parseMode(search) {
  return new URLSearchParams(search).get("data") === "synthetic" ? "synthetic" : "real";
}

/** "Hood River" -> "hood-river" (used in #county-... links). */
export function slug(name) {
  return String(name).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

/**
 * Which of the three data states applies: "synthetic", "loaded" (county approvals present)
 * or "pending" (no county approvals loaded yet).
 */
export function dataState(mode, section) {
  if (mode === "synthetic") return "synthetic";
  const county = section?.source_types?.county;
  return county && county.n_projects > 0 ? "loaded" : "pending";
}

/** Map class for a count: null = no data yet, 0 none, 1, 2, 3 (3-4), 4 (5-9), 5 (10+). */
export function classFor(n) {
  if (n === null || n === undefined) return null;
  if (n <= 0) return 0;
  if (n <= 2) return n;
  if (n <= 4) return 3;
  if (n <= 9) return 4;
  return 5;
}

/** Display for an outcome value; a missing outcome reads "Not in our records". */
export function outcomeView(value) {
  return OUTCOMES[value] ?? { tone: "neutral", label: "Not in our records" };
}

/** "1 approval" / "2 approvals". */
export function plural(n, one, many = one + "s") {
  return `${n} ${n === 1 ? one : many}`;
}

/** Bar rows for the county-records chart: widths are relative to the largest count. */
export function chartRows(categories, field) {
  const max = Math.max(0, ...categories.map((c) => c[field]));
  return categories.map((c) => ({
    id: c.id,
    label: c.label,
    count: c[field],
    pct: max === 0 ? 0 : (c[field] / max) * 100,
  }));
}

// ---- map ---------------------------------------------------------------------------------

const RAD = Math.PI / 180;

/** Lambert conformal conic with Oregon's usual parameters; returns [x, y] with y pointing up. */
export function makeProjection({ lat1 = 43, lat2 = 45.5, lat0 = 41.75, lon0 = -120.5 } = {}) {
  const t = (phi) => Math.tan(Math.PI / 4 + phi / 2);
  const p1 = lat1 * RAD;
  const p2 = lat2 * RAD;
  const n = Math.log(Math.cos(p1) / Math.cos(p2)) / Math.log(t(p2) / t(p1));
  const F = (Math.cos(p1) * t(p1) ** n) / n;
  const rho = (phi) => F / t(phi) ** n;
  const rho0 = rho(lat0 * RAD);
  return (lon, lat) => {
    const r = rho(lat * RAD);
    const theta = n * (lon - lon0) * RAD;
    return [r * Math.sin(theta), rho0 - r * Math.cos(theta)];
  };
}

function polygons(geometry) {
  return geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
}

function ringCentroid(ring) {
  let a = 0;
  let cx = 0;
  let cy = 0;
  for (let i = 0; i < ring.length - 1; i++) {
    const [x0, y0] = ring[i];
    const [x1, y1] = ring[i + 1];
    const cross = x0 * y1 - x1 * y0;
    a += cross;
    cx += (x0 + x1) * cross;
    cy += (y0 + y1) * cross;
  }
  if (a === 0) return { area: 0, x: ring[0][0], y: ring[0][1] };
  return { area: Math.abs(a / 2), x: cx / (3 * a), y: cy / (3 * a) };
}

/**
 * Projects county GeoJSON into SVG coordinates that fit the box.
 * Returns [{fips, name, slug, d, cx, cy}] sorted by name (cx, cy = label point).
 */
export function buildMap(geojson, { width = 600, height = 460, pad = 6 } = {}) {
  const project = makeProjection();
  const feats = geojson.features.map((f) => ({
    f,
    polys: polygons(f.geometry).map((poly) =>
      poly.map((ring) => ring.map(([lon, lat]) => project(lon, lat))),
    ),
  }));
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  for (const { polys } of feats)
    for (const poly of polys)
      for (const ring of poly)
        for (const [x, y] of ring) {
          minX = Math.min(minX, x);
          maxX = Math.max(maxX, x);
          minY = Math.min(minY, y);
          maxY = Math.max(maxY, y);
        }
  const scale = Math.min((width - 2 * pad) / (maxX - minX), (height - 2 * pad) / (maxY - minY));
  const ox = (width - (maxX - minX) * scale) / 2;
  const oy = (height - (maxY - minY) * scale) / 2;
  const sx = (x) => ox + (x - minX) * scale;
  const sy = (y) => oy + (maxY - y) * scale;
  const r1 = (v) => Math.round(v * 10) / 10;

  return feats
    .map(({ f, polys }) => {
      const d = polys
        .map((poly) =>
          poly
            .map(
              (ring) =>
                "M" + ring.map(([x, y]) => `${r1(sx(x))},${r1(sy(y))}`).join("L") + "Z",
            )
            .join(""),
        )
        .join("");
      let best = { area: -1, x: 0, y: 0 };
      for (const poly of polys) {
        const c = ringCentroid(poly[0].map(([x, y]) => [sx(x), sy(y)]));
        if (c.area > best.area) best = c;
      }
      return {
        fips: f.properties.fips,
        name: f.properties.name,
        slug: slug(f.properties.name),
        d,
        cx: r1(best.x),
        cy: r1(best.y),
      };
    })
    .sort((a, b) => a.name.localeCompare(b.name));
}

/**
 * Arrow-key navigation: the nearest item whose label point lies in that direction.
 * Returns the item, or null if there is none that way.
 */
export function nearestInDirection(current, items, direction) {
  const vec = { left: [-1, 0], right: [1, 0], up: [0, -1], down: [0, 1] }[direction];
  if (!vec) return null;
  let best = null;
  let bestScore = Infinity;
  for (const it of items) {
    if (it === current) continue;
    const dx = it.cx - current.cx;
    const dy = it.cy - current.cy;
    const along = dx * vec[0] + dy * vec[1];
    const across = Math.abs(dx * vec[1] - dy * vec[0]);
    if (along <= 0 || across > along * 2) continue;
    const score = along + 2 * across;
    if (score < bestScore) {
      best = it;
      bestScore = score;
    }
  }
  return best;
}

// ---- data views --------------------------------------------------------------------------

/** County records by FIPS for the map and table: {fips: n}, or null while none are loaded. */
export function countyCounts(section) {
  const county = section?.source_types?.county;
  if (!county || county.n_projects === 0) return null;
  const out = {};
  for (const [fips, c] of Object.entries(county.by_county)) out[fips] = c.n_projects;
  return out;
}

/** County-record projects in one county, sorted by id. */
export function countyProjects(section, fips) {
  return section.projects
    .filter((p) => p.source_type === "county" && p.fips === fips)
    .sort((a, b) => a.id.localeCompare(b.id));
}

/** The appeal-example cases (LUBA source type) in a section; synthetic data has none. */
export function appealCases(section) {
  return (section.cases ?? []).filter((c) => c.project.source_type === "luba");
}

/** Reasons for a chart: county records use "local"; LUBA examples use local and appeal. */
export function reasonTotals(block) {
  return {
    reasons: block.reasons,
    handChecked: block.hand_checked,
    machine: block.reasons - block.hand_checked,
  };
}

/** Name of the document a reason's quote comes from: "LUBA opinion". */
export function docLabel(documents, reason) {
  const doc = documents.find((d) => d.id === reason.document_id);
  return DOC_LABELS[doc?.document_type] ?? DOC_LABELS.other;
}

/** Source line for a quote: "LUBA opinion, page 23". */
export function sourceLine(documents, reason) {
  return `${docLabel(documents, reason)}, page ${reason.pdf_page}`;
}
