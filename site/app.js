// Placeholder page: draws the county map and tables from the two data files.
// Everything is read with relative paths so it works under a GitHub Pages sub-path.
// Text is set with textContent only (never innerHTML), so data can never inject markup.
"use strict";

const SVG_NS = "http://www.w3.org/2000/svg";

async function load() {
  const [site, geo] = await Promise.all([
    fetch("data/site-data.json").then((r) => r.json()),
    fetch("data/oregon-counties.geojson").then((r) => r.json()),
  ]);
  const state = { section: "real", source: null };
  const $ = (id) => document.getElementById(id);

  function sourceTypes() {
    return Object.keys(site[state.section].source_types);
  }

  function fillSources() {
    const sel = $("source");
    sel.replaceChildren();
    for (const st of sourceTypes()) {
      const o = document.createElement("option");
      o.value = st;
      o.textContent = st;
      sel.appendChild(o);
    }
    state.source = sourceTypes()[0] ?? null;
    sel.value = state.source ?? "";
  }

  function drawMap(byCounty) {
    const svg = $("map");
    svg.replaceChildren();
    const rings = (g) => (g.type === "Polygon" ? [g.coordinates] : g.coordinates);
    let minLon = Infinity, maxLon = -Infinity, minLat = Infinity, maxLat = -Infinity;
    for (const f of geo.features)
      for (const poly of rings(f.geometry))
        for (const [lon, lat] of poly[0]) {
          minLon = Math.min(minLon, lon); maxLon = Math.max(maxLon, lon);
          minLat = Math.min(minLat, lat); maxLat = Math.max(maxLat, lat);
        }
    const k = Math.cos(((minLat + maxLat) / 2) * Math.PI / 180);
    const scale = Math.min(580 / ((maxLon - minLon) * k), 420 / (maxLat - minLat));
    const x = (lon) => 10 + (lon - minLon) * k * scale;
    const y = (lat) => 10 + (maxLat - lat) * scale;
    const max = Math.max(1, ...Object.values(byCounty).map((c) => c.n_projects));
    for (const f of geo.features) {
      const info = byCounty[f.properties.fips];
      const d = rings(f.geometry)
        .map((poly) => poly.map((ring) => "M" + ring.map(([lo, la]) => `${x(lo).toFixed(1)},${y(la).toFixed(1)}`).join("L") + "Z").join(""))
        .join("");
      const p = document.createElementNS(SVG_NS, "path");
      p.setAttribute("d", d);
      p.setAttribute("fill", info ? "var(--accent)" : "var(--line)");
      p.setAttribute("fill-opacity", info ? String(0.25 + 0.75 * (info.n_projects / max)) : "0.35");
      const t = document.createElementNS(SVG_NS, "title");
      t.textContent = `${f.properties.name}: ${info ? info.n_projects : 0} project(s)`;
      p.appendChild(t);
      svg.appendChild(p);
    }
  }

  function row(cells) {
    const tr = document.createElement("tr");
    for (const c of cells) {
      const td = document.createElement("td");
      td.textContent = String(c);
      tr.appendChild(td);
    }
    return tr;
  }

  function render() {
    const sec = site[state.section];
    const block = sec.source_types[state.source];
    const notice = $("notice");
    notice.hidden = state.section !== "synthetic";
    notice.textContent = state.section === "synthetic" ? site.meta.synthetic_notice : "";
    if (!block) {
      $("summary").textContent = "No records.";
      return;
    }
    const L = site.meta.labels;
    const co = block.county_outcomes, ao = block.appeal_outcomes;
    $("summary").textContent =
      `${block.n_projects} project(s), ${block.reasons} coded reason(s) (${block.hand_checked} hand-checked). ` +
      `${L.county_outcome}: ${Object.entries(co).map(([k, v]) => `${k.replaceAll("_", " ")} ${v}`).join(", ")}. ` +
      `${L.appeal_outcome}: ${Object.entries(ao).map(([k, v]) => `${k} ${v}`).join(", ")}.`;
    drawMap(block.by_county);
    const cb = document.querySelector("#counties tbody");
    cb.replaceChildren(
      ...Object.entries(block.by_county)
        .sort((a, b) => a[1].name.localeCompare(b[1].name))
        .map(([, c]) => row([c.name, c.n_projects])),
    );
    const tb = document.querySelector("#categories tbody");
    tb.replaceChildren(...block.categories.map((c) => row([c.label, c.count, c.local, c.appeal])));
  }

  for (const r of document.querySelectorAll('input[name="section"]'))
    r.addEventListener("change", () => {
      state.section = r.value;
      fillSources();
      render();
    });
  $("source").addEventListener("change", (e) => {
    state.source = e.target.value;
    render();
  });
  fillSources();
  render();
}

load().catch((err) => {
  document.getElementById("summary").textContent = "Could not load the data: " + err.message;
});
