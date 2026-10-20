"""Tests for the Oregon county boundary build (no network: the fetcher is injected)."""

import json
from datetime import date
from pathlib import Path

import pytest

from conftest import REPO_ROOT
from oregon_farmland_solar import geo
from oregon_farmland_solar.cli import main
from oregon_farmland_solar.synthetic import OREGON_COUNTIES

COMMITTED = REPO_ROOT / "data" / "geo" / "oregon-counties.geojson"
COMMITTED_PROV = REPO_ROOT / "data" / "geo" / "oregon-counties.provenance.json"
MAX_COMMITTED_BYTES = 1_000_000
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


@pytest.mark.skipif(not COMMITTED.exists(), reason="county boundaries not built yet")
def test_committed_file_is_small_enough_for_a_web_page():
    assert COMMITTED.stat().st_size <= MAX_COMMITTED_BYTES


@pytest.mark.skipif(not COMMITTED.exists(), reason="county boundaries not built yet")
def test_committed_file_matches_its_provenance_checksum():
    prov = json.loads(COMMITTED_PROV.read_text())
    assert prov["derived_sha256"] == geo.sha256_hex(COMMITTED.read_bytes())


def _fake_mapshaper(calls):
    """A runner that 'simplifies' by copying the input file, and records how it was called."""

    def run(cmd):
        calls.append(cmd)
        src = cmd[cmd.index("mapshaper@" + geo.MAPSHAPER_VERSION) + 1]
        out = cmd[cmd.index("-o") + 1]
        Path(out).write_bytes(Path(src).read_bytes())

    return run


def _built(tmp_path):
    raw_bytes = json.dumps(_raw()).encode()
    geo.build_counties(
        lambda url: raw_bytes, tmp_path / "geo", tmp_path / "raw", date(2026, 10, 20)
    )
    return tmp_path / "geo", tmp_path / "raw"


def test_build_also_keeps_the_full_resolution_file_locally(tmp_path):
    out_dir, raw_dir = _built(tmp_path)
    assert (raw_dir / geo.FULL_NAME).exists()
    assert (out_dir / geo.DERIVED_NAME).read_bytes() == (raw_dir / geo.FULL_NAME).read_bytes()


def test_simplify_runs_pinned_mapshaper_with_the_percentage(tmp_path):
    out_dir, raw_dir = _built(tmp_path)
    calls = []
    geo.simplify_counties(out_dir, raw_dir, 5, runner=_fake_mapshaper(calls))
    cmd = calls[0]
    assert cmd[:3] == ["npx", "--yes", f"mapshaper@{geo.MAPSHAPER_VERSION}"]
    assert "5%" in cmd
    assert "keep-shapes" in cmd


def test_simplify_updates_the_provenance(tmp_path):
    out_dir, raw_dir = _built(tmp_path)
    before = json.loads((out_dir / geo.PROVENANCE_NAME).read_text())
    geo.simplify_counties(out_dir, raw_dir, 5, runner=_fake_mapshaper([]))
    after = json.loads((out_dir / geo.PROVENANCE_NAME).read_text())
    assert after["raw_sha256"] == before["raw_sha256"]
    assert after["full_resolution_sha256"] == before["derived_sha256"]
    assert after["derived_sha256"] == geo.sha256_hex((out_dir / geo.DERIVED_NAME).read_bytes())
    assert after["simplification"]["percent"] == 5
    assert after["simplification"]["tool"] == f"mapshaper {geo.MAPSHAPER_VERSION}"


def test_simplify_keeps_36_features_and_properties_one_feature_per_line(tmp_path):
    out_dir, raw_dir = _built(tmp_path)
    geo.simplify_counties(out_dir, raw_dir, 5, runner=_fake_mapshaper([]))
    text = (out_dir / geo.DERIVED_NAME).read_text()
    data = json.loads(text)
    assert len(data["features"]) == 36
    assert all(set(f["properties"]) == {"fips", "name", "cobcode"} for f in data["features"])
    assert len(text.strip().splitlines()) == 38  # header, 36 features, footer


def test_simplify_rejects_a_result_that_lost_counties(tmp_path):
    out_dir, raw_dir = _built(tmp_path)

    def lossy(cmd):
        out = cmd[cmd.index("-o") + 1]
        data = json.loads(
            Path(cmd[cmd.index("mapshaper@" + geo.MAPSHAPER_VERSION) + 1]).read_text()
        )
        data["features"] = data["features"][:35]
        Path(out).write_text(json.dumps(data))

    with pytest.raises(ValueError, match="36"):
        geo.simplify_counties(out_dir, raw_dir, 5, runner=lossy)


def test_simplify_percent_must_be_between_0_and_100(tmp_path):
    out_dir, raw_dir = _built(tmp_path)
    for bad in (0, 100, -5, 150):
        with pytest.raises(ValueError):
            geo.simplify_counties(out_dir, raw_dir, bad, runner=_fake_mapshaper([]))


def test_simplify_needs_the_full_resolution_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        geo.simplify_counties(tmp_path / "geo", tmp_path / "raw", 5, runner=_fake_mapshaper([]))


def test_cli_simplify_counties(tmp_path, monkeypatch):
    out_dir, raw_dir = _built(tmp_path)
    monkeypatch.setattr(geo, "run_command", _fake_mapshaper([]))
    code = main(
        [
            "simplify-counties",
            "--percent",
            "5",
            "--out-dir",
            str(out_dir),
            "--raw-dir",
            str(raw_dir),
        ]
    )
    assert code == 0
