"""Tests for the Oregon county boundary build (no network: the fetcher is injected)."""

import json
from datetime import date

import pytest

from conftest import REPO_ROOT
from oregon_farmland_solar import geo
from oregon_farmland_solar.cli import main
from oregon_farmland_solar.synthetic import OREGON_COUNTIES

COMMITTED = REPO_ROOT / "data" / "geo" / "oregon-counties.geojson"
WA_DUPLICATES = ("BENTON", "COLUMBIA", "DOUGLAS", "GRANT", "JEFFERSON", "LINCOLN")


def _square(x: float) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [[[x, 45], [x + 1, 45], [x + 1, 46], [x, 46], [x, 45]]],
    }


def _feature(name: str, code: str, x: float = 0) -> dict:
    return {
        "type": "Feature",
        "properties": {"COUNTY_NAME": name, "COBCODE": code},
        "geometry": _square(x),
    }


def _raw() -> dict:
    """A fake BLM response: 36 Oregon counties plus Washington counties, some sharing names."""
    feats = [
        _feature(name.upper(), f"OR{2 * i + 1:03d}", x=i) for i, name in enumerate(OREGON_COUNTIES)
    ]
    for i, name in enumerate(WA_DUPLICATES):
        feats.append(_feature(name, f"WA{2 * i + 5:03d}", x=100 + i))
    feats.append(_feature("KING", "WA033", x=200))
    return {"type": "FeatureCollection", "features": feats}


def test_oregon_fips_covers_every_county_once():
    assert set(geo.OREGON_FIPS) == set(OREGON_COUNTIES)
    assert len(set(geo.OREGON_FIPS.values())) == 36
    assert geo.OREGON_FIPS["Josephine"] == "41033"


def test_keeps_only_the_36_oregon_counties():
    out = geo.oregon_counties(_raw())
    assert len(out["features"]) == 36
    assert {f["properties"]["name"] for f in out["features"]} == set(OREGON_COUNTIES)


def test_washington_counties_with_oregon_names_are_excluded():
    out = geo.oregon_counties(_raw())
    by_name = {f["properties"]["name"]: f["properties"]["fips"] for f in out["features"]}
    assert by_name["Columbia"] == "41009"
    assert by_name["Benton"] == "41003"


def test_names_are_matched_case_insensitively():
    out = geo.oregon_counties(_raw())
    assert "Hood River" in {f["properties"]["name"] for f in out["features"]}


def test_fips_is_41_plus_the_code_digits():
    out = geo.oregon_counties(_raw())
    for f in out["features"]:
        assert f["properties"]["fips"] == "41" + f["properties"]["cobcode"][2:]


def test_properties_are_exactly_fips_name_and_cobcode():
    out = geo.oregon_counties(_raw())
    assert all(set(f["properties"]) == {"fips", "name", "cobcode"} for f in out["features"])


def test_geometry_is_passed_through_unchanged():
    raw = _raw()
    originals = {f["properties"]["COBCODE"]: f["geometry"] for f in raw["features"]}
    out = geo.oregon_counties(raw)
    assert all(f["geometry"] == originals[f["properties"]["cobcode"]] for f in out["features"])


def test_output_is_sorted_by_fips():
    fips = [f["properties"]["fips"] for f in geo.oregon_counties(_raw())["features"]]
    assert fips == sorted(fips)


def test_missing_county_is_an_error():
    raw = _raw()
    raw["features"] = [f for f in raw["features"] if f["properties"]["COBCODE"] != "OR033"]
    with pytest.raises(ValueError, match="36"):
        geo.oregon_counties(raw)


def test_unknown_county_name_is_an_error():
    raw = _raw()
    raw["features"][0]["properties"]["COUNTY_NAME"] = "ATLANTIS"
    with pytest.raises(ValueError, match="ATLANTIS"):
        geo.oregon_counties(raw)


def test_name_and_code_that_disagree_is_an_error():
    raw = _raw()
    raw["features"][0]["properties"]["COBCODE"] = "OR071"  # Baker with Yamhill's code
    with pytest.raises(ValueError, match="BAKER"):
        geo.oregon_counties(raw)


def test_build_writes_unmodified_raw_derived_and_provenance(tmp_path):
    raw_bytes = json.dumps(_raw()).encode()
    result = geo.build_counties(
        fetcher=lambda url: raw_bytes,
        out_dir=tmp_path / "geo",
        raw_dir=tmp_path / "raw",
        today=date(2026, 10, 20),
    )
    assert (tmp_path / "raw" / "blm-or-county-boundaries.geojson").read_bytes() == raw_bytes
    derived = json.loads((tmp_path / "geo" / "oregon-counties.geojson").read_text())
    assert len(derived["features"]) == 36
    prov = json.loads((tmp_path / "geo" / "oregon-counties.provenance.json").read_text())
    assert prov["accessed"] == "2026-10-20"
    assert prov["raw_sha256"] == geo.sha256_hex(raw_bytes)
    assert prov["credit"].startswith("Bureau of Land Management")
    assert prov["feature_count_raw"] == 43
    assert prov["feature_count_derived"] == 36
    assert result["raw_sha256"] == prov["raw_sha256"]


def test_build_is_deterministic(tmp_path):
    raw_bytes = json.dumps(_raw()).encode()
    for d in ("a", "b"):
        geo.build_counties(
            lambda url: raw_bytes, tmp_path / d, tmp_path / "raw", date(2026, 10, 20)
        )
    assert (tmp_path / "a" / "oregon-counties.geojson").read_bytes() == (
        tmp_path / "b" / "oregon-counties.geojson"
    ).read_bytes()


def test_cli_counties_uses_the_fetcher(tmp_path, monkeypatch):
    monkeypatch.setattr(geo, "fetch_layer", lambda url: json.dumps(_raw()).encode())
    code = main(["counties", "--out-dir", str(tmp_path / "g"), "--raw-dir", str(tmp_path / "r")])
    assert code == 0
    assert (tmp_path / "g" / "oregon-counties.geojson").exists()


@pytest.mark.skipif(not COMMITTED.exists(), reason="county boundaries not built yet")
def test_committed_file_has_the_36_oregon_counties():
    data = json.loads(COMMITTED.read_text())
    assert {f["properties"]["name"] for f in data["features"]} == set(OREGON_COUNTIES)
    assert len(data["features"]) == 36
