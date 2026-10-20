"""Builds the Oregon county boundary layer used by the map.

Source: the Bureau of Land Management (BLM) county boundaries feature layer, hosted on the
Oregon GeoHub. It covers Oregon and Washington, so the build keeps only the 36 Oregon counties
(feature codes starting with ``OR``) and checks the result against our own county list.

Principles (see ``docs/data-sources.md``):

* The server response is saved byte for byte and never edited; only a separate derived file
  is changed.
* Official attributes are not rewritten. The derived file keeps the source code as ``cobcode``
  and adds only our join keys, ``fips`` and ``name``.
* Geometry is passed through unchanged. Any later generalization must be recorded separately.
* A provenance file records the source, access date, checksums and every step.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import urllib.request
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

from .synthetic import OREGON_COUNTIES

SERVICE_URL = (
    "https://services1.arcgis.com/KbxwQRRfWyEYLgp4/arcgis/rest/services/"
    "BLM_OR_County_Boundaries_Polygon_Hub/FeatureServer/1"
)
# Asks the server for GeoJSON in WGS84 longitude/latitude (EPSG:4326). The layer itself is
# stored in NAD83 (EPSG:4269); the server does the conversion, and provenance notes it.
QUERY_URL = f"{SERVICE_URL}/query?where=1%3D1&outFields=COUNTY_NAME,COBCODE&outSR=4326&f=geojson"
ITEM_PAGE = "https://geohub.oregon.gov/datasets/51d396ec311d449fa2f6cb1141d496f2_1"
CREDIT = "Bureau of Land Management (BLM), Oregon State Office"

RAW_NAME = "blm-or-county-boundaries.geojson"
# Full-resolution Oregon counties (kept locally, git-ignored); the committed file may be simplified.
FULL_NAME = "oregon-counties.full.geojson"
DERIVED_NAME = "oregon-counties.geojson"
PROVENANCE_NAME = "oregon-counties.provenance.json"

# County FIPS codes (state 41), checked against the source layer's feature codes.
OREGON_FIPS: dict[str, str] = {
    "Baker": "41001",
    "Benton": "41003",
    "Clackamas": "41005",
    "Clatsop": "41007",
    "Columbia": "41009",
    "Coos": "41011",
    "Crook": "41013",
    "Curry": "41015",
    "Deschutes": "41017",
    "Douglas": "41019",
    "Gilliam": "41021",
    "Grant": "41023",
    "Harney": "41025",
    "Hood River": "41027",
    "Jackson": "41029",
    "Jefferson": "41031",
    "Josephine": "41033",
    "Klamath": "41035",
    "Lake": "41037",
    "Lane": "41039",
    "Lincoln": "41041",
    "Linn": "41043",
    "Malheur": "41045",
    "Marion": "41047",
    "Morrow": "41049",
    "Multnomah": "41051",
    "Polk": "41053",
    "Sherman": "41055",
    "Tillamook": "41057",
    "Umatilla": "41059",
    "Union": "41061",
    "Wallowa": "41063",
    "Wasco": "41065",
    "Washington": "41067",
    "Wheeler": "41069",
    "Yamhill": "41071",
}

_BY_UPPER_NAME = {name.upper(): name for name in OREGON_COUNTIES}

# Pinned so a simplification can be reproduced exactly; run through npx (needs Node.js).
MAPSHAPER_VERSION = "0.7.92"

Fetcher = Callable[[str], bytes]
Runner = Callable[[list[str]], None]


def sha256_hex(data: bytes) -> str:
    """Returns the SHA-256 of ``data`` as lowercase hex."""
    return hashlib.sha256(data).hexdigest()


def fetch_layer(url: str) -> bytes:
    """Downloads ``url`` over HTTPS and returns the response bytes unchanged.

    Args:
        url: An ``https://`` address.

    Returns:
        The raw response body.

    Raises:
        ValueError: If the address is not HTTPS.
    """
    if not url.startswith("https://"):
        raise ValueError("only https URLs are allowed")
    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310 (scheme checked above)
        return resp.read()


def run_command(cmd: list[str]) -> None:
    """Runs a command and raises if it fails.

    Args:
        cmd: The command and its arguments.

    Raises:
        subprocess.CalledProcessError: If the command exits with an error.
    """
    subprocess.run(cmd, check=True)  # noqa: S603 (fixed argument list, no shell)


def oregon_counties(raw: dict[str, Any]) -> dict[str, Any]:
    """Keeps the Oregon counties from the source layer and adds the join keys.

    Washington features are dropped by their ``OR`` / ``WA`` code prefix, not by name, because
    six county names (Benton, Columbia, Douglas, Grant, Jefferson, Lincoln) exist in both
    states. Geometry is not touched.

    Args:
        raw: The parsed GeoJSON FeatureCollection from the source layer.

    Returns:
        A FeatureCollection of exactly 36 features sorted by FIPS code. Each has the properties
        ``fips``, ``name`` and ``cobcode`` (the source code, unchanged).

    Raises:
        ValueError: If a county name is unknown, a name and its code disagree, a county is
            repeated, or the result is not exactly the 36 Oregon counties.
    """
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for feat in raw["features"]:
        code = str(feat["properties"]["COBCODE"])
        if not code.startswith("OR"):
            continue
        source_name = str(feat["properties"]["COUNTY_NAME"])
        name = _BY_UPPER_NAME.get(source_name.upper())
        if name is None:
            raise ValueError(f"unknown Oregon county name in source layer: {source_name!r}")
        fips = "41" + code[2:]
        if fips != OREGON_FIPS[name]:
            raise ValueError(
                f"{source_name}: code {code} does not match expected {OREGON_FIPS[name]}"
            )
        if fips in seen:
            raise ValueError(f"duplicate county in source layer: {source_name} ({code})")
        seen.add(fips)
        out.append(
            {
                "type": "Feature",
                "properties": {"fips": fips, "name": name, "cobcode": code},
                "geometry": feat["geometry"],
            }
        )
    if len(out) != len(OREGON_COUNTIES):
        raise ValueError(f"expected {len(OREGON_COUNTIES)} Oregon counties, found {len(out)}")
    out.sort(key=lambda f: f["properties"]["fips"])
    return {"type": "FeatureCollection", "features": out}


def _dump_collection(fc: dict[str, Any]) -> str:
    """Serializes a FeatureCollection compactly with one feature per line (readable diffs)."""
    rows = ",\n".join(
        json.dumps(f, separators=(",", ":"), ensure_ascii=False) for f in fc["features"]
    )
    return '{"type":"FeatureCollection","features":[\n' + rows + "\n]}\n"


def build_counties(
    fetcher: Fetcher,
    out_dir: Path,
    raw_dir: Path,
    today: date,
) -> dict[str, Any]:
    """Fetches the layer, saves it unmodified, and writes the derived file and provenance.

    Args:
        fetcher: Function that returns the response bytes for a URL (``fetch_layer`` for real
            runs, a fake in tests).
        out_dir: Folder for the derived GeoJSON and the provenance file (committed to git).
        raw_dir: Folder for the unmodified server response (git-ignored, kept locally).
        today: Access date to record.

    Returns:
        The provenance record that was written.
    """
    raw_bytes = fetcher(QUERY_URL)
    raw = json.loads(raw_bytes)
    derived = oregon_counties(raw)
    derived_text = _dump_collection(derived)

    raw_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / RAW_NAME).write_bytes(raw_bytes)
    (raw_dir / FULL_NAME).write_text(derived_text, encoding="utf-8")
    (out_dir / DERIVED_NAME).write_text(derived_text, encoding="utf-8")

    prov = {
        "layer": "BLM OR County Boundaries Polygon Hub",
        "item_page": ITEM_PAGE,
        "service_url": SERVICE_URL,
        "query_url": QUERY_URL,
        "credit": CREDIT,
        "terms": (
            "Provided by BLM 'as is'. Cite BLM as the source of derived products; describe any "
            "modifications and do not imply BLM endorsed them; not a legal document or survey; "
            "BLM may update the data without notice."
        ),
        "accessed": today.isoformat(),
        "raw_file": f"data/raw/geo/{RAW_NAME} (kept locally, not committed)",
        "raw_sha256": sha256_hex(raw_bytes),
        "derived_file": f"data/geo/{DERIVED_NAME}",
        "derived_sha256": sha256_hex(derived_text.encode("utf-8")),
        "feature_count_raw": len(raw["features"]),
        "feature_count_derived": len(derived["features"]),
        "steps": [
            "Requested GeoJSON from the layer's query service with outSR=4326 (server reprojects "
            "from NAD83 to WGS84 longitude/latitude).",
            "Kept features whose COBCODE starts with 'OR' (the layer also holds Washington).",
            "Added fips ('41' + the three digits of COBCODE) and name (matched to our "
            "county list); kept COBCODE as cobcode. The query asked only for COUNTY_NAME and "
            "COBCODE, so no other source attributes were requested.",
            "Geometry unchanged; no simplification applied.",
            "Checked: exactly 36 counties, unique FIPS, name and code agree.",
        ],
    }
    (out_dir / PROVENANCE_NAME).write_text(json.dumps(prov, indent=2) + "\n", encoding="utf-8")
    return prov


def simplify_counties(
    out_dir: Path,
    raw_dir: Path,
    percent: float,
    runner: Runner | None = None,
) -> dict[str, Any]:
    """Simplifies the county geometry for the web and records it in the provenance file.

    Uses mapshaper, which simplifies shared borders together so neighboring counties still
    fit with no gaps or overlaps (simplifying each polygon alone would not). The full
    resolution file in ``raw_dir`` is the input and is never changed. The result replaces the
    committed derived file in ``out_dir``.

    Args:
        out_dir: Folder with the derived file and provenance (committed to git).
        raw_dir: Folder with the full-resolution file written by ``build_counties``.
        percent: Share of vertices to keep, greater than 0 and less than 100.
        runner: Function that runs a command; defaults to ``run_command``. Tests inject a fake.

    Returns:
        The updated provenance record.

    Raises:
        ValueError: If ``percent`` is out of range or the result does not have exactly the 36
            Oregon counties with the expected properties.
        FileNotFoundError: If the full-resolution file or the provenance file is missing.
    """
    if not 0 < percent < 100:
        raise ValueError("percent must be greater than 0 and less than 100")
    full = raw_dir / FULL_NAME
    prov_path = out_dir / PROVENANCE_NAME
    if not full.exists() or not prov_path.exists():
        raise FileNotFoundError(f"run `ofs counties` first: need {full} and {prov_path}")
    run = runner or run_command

    tmp = raw_dir / "oregon-counties.simplified.tmp.geojson"
    cmd = [
        "npx",
        "--yes",
        f"mapshaper@{MAPSHAPER_VERSION}",
        str(full),
        "-simplify",
        f"{percent:g}%",
        "keep-shapes",
        "-o",
        str(tmp),
        "precision=0.0001",
    ]
    run(cmd)

    result = json.loads(tmp.read_text(encoding="utf-8"))
    tmp.unlink()
    if len(result["features"]) != len(OREGON_COUNTIES):
        raise ValueError(
            f"expected {len(OREGON_COUNTIES)} counties after simplifying, "
            f"found {len(result['features'])}"
        )
    if any(set(f["properties"]) != {"fips", "name", "cobcode"} for f in result["features"]):
        raise ValueError("simplified features lost or gained properties")
    text = _dump_collection(result)
    (out_dir / DERIVED_NAME).write_text(text, encoding="utf-8")

    prov = json.loads(prov_path.read_text(encoding="utf-8"))
    prov["full_resolution_sha256"] = sha256_hex(full.read_bytes())
    prov["derived_sha256"] = sha256_hex(text.encode("utf-8"))
    prov["simplification"] = {
        "tool": f"mapshaper {MAPSHAPER_VERSION}",
        "command": " ".join(
            cmd[:3] + ["<full-resolution file>"] + cmd[4:8] + ["<output>"] + cmd[9:]
        ),
        "percent": percent,
        "note": (
            "Generalized for display; shared borders simplified together. Not for measurement "
            "or legal use. The full-resolution file is rebuilt by `ofs counties`."
        ),
    }
    prov["steps"] = [
        step for step in prov["steps"] if not step.startswith("Geometry unchanged")
    ] + [
        f"Simplified geometry to {percent:g}% of vertices with mapshaper {MAPSHAPER_VERSION} "
        "(keep-shapes, coordinate precision 0.0001 degrees), then re-checked 36 features and "
        "properties.",
    ]
    prov_path.write_text(json.dumps(prov, indent=2) + "\n", encoding="utf-8")
    return prov
