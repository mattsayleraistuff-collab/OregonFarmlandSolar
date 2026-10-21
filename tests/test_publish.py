"""Tests for staging the static site for GitHub Pages, and for the site's own files."""

import re

import pytest

from conftest import REPO_ROOT
from oregon_farmland_solar import publish
from oregon_farmland_solar.cli import main

SITE = REPO_ROOT / "site"


def _make_site(root, extra=()):
    site = root / "site"
    (site / "data").mkdir(parents=True)
    (site / "index.html").write_text("<html></html>")
    (site / "app.js").write_text("//")
    (site / "data" / "site-data.json").write_text("{}")
    for name in extra:
        (site / name).write_text("x")
    geo = root / "oregon-counties.geojson"
    geo.write_text('{"type":"FeatureCollection","features":[]}')
    return site, geo


def test_stage_copies_site_and_places_the_county_layer(tmp_path):
    site, geo = _make_site(tmp_path)
    out = tmp_path / "_site"
    publish.stage_site(site, geo, out)
    assert (out / "index.html").read_text() == "<html></html>"
    assert (out / "app.js").exists()
    assert (out / "data" / "site-data.json").exists()
    assert (out / "data" / "oregon-counties.geojson").read_text() == geo.read_text()


def test_stage_replaces_an_existing_output_folder(tmp_path):
    site, geo = _make_site(tmp_path)
    out = tmp_path / "_site"
    out.mkdir()
    (out / "stale.html").write_text("old")
    publish.stage_site(site, geo, out)
    assert not (out / "stale.html").exists()


@pytest.mark.parametrize("missing", ["index.html", "data/site-data.json"])
def test_stage_requires_the_page_and_the_site_data(tmp_path, missing):
    site, geo = _make_site(tmp_path)
    (site / missing).unlink()
    with pytest.raises(FileNotFoundError, match=re.escape(missing)):
        publish.stage_site(site, geo, tmp_path / "_site")


def test_stage_requires_the_county_layer(tmp_path):
    site, geo = _make_site(tmp_path)
    geo.unlink()
    with pytest.raises(FileNotFoundError):
        publish.stage_site(site, geo, tmp_path / "_site")


@pytest.mark.parametrize("bad", ["notes.pdf", "secrets.env", "key.pem", "run.py", ".env"])
def test_stage_refuses_files_that_should_never_be_published(tmp_path, bad):
    site, geo = _make_site(tmp_path, extra=[bad])
    with pytest.raises(ValueError, match=re.escape(bad)):
        publish.stage_site(site, geo, tmp_path / "_site")
    assert not (tmp_path / "_site").exists()


def test_output_folder_may_not_be_inside_the_site_folder(tmp_path):
    site, geo = _make_site(tmp_path)
    with pytest.raises(ValueError):
        publish.stage_site(site, geo, site / "out")


def test_cli_stage_site(tmp_path):
    site, geo = _make_site(tmp_path)
    out = tmp_path / "_site"
    code = main(["stage-site", "--site-dir", str(site), "--geo", str(geo), "--out", str(out)])
    assert code == 0
    assert (out / "data" / "oregon-counties.geojson").exists()


# --- checks on the real site files -------------------------------------------------------

_EXTERNAL_LOAD = re.compile(
    r"""<(?:script|img|link|iframe|source)\b[^>]*\b(?:src|href)\s*=\s*["']?(?:https?:)?//"""
    r"""|fetch\(\s*["'`]\s*(?:https?:)?//"""
    r"""|@import|url\(\s*["']?(?:https?:)?//""",
    re.IGNORECASE,
)


def _site_text_files():
    return [p for p in SITE.rglob("*") if p.suffix in {".html", ".js", ".css"}]


def test_the_real_site_stages_cleanly(tmp_path):
    publish.stage_site(SITE, REPO_ROOT / "data" / "geo" / "oregon-counties.geojson", tmp_path / "o")


def test_the_site_loads_nothing_from_other_servers():
    """No third-party requests: no tracking, no tile servers, nothing a browser leaks to."""
    files = _site_text_files()
    assert files
    for p in files:
        assert not _EXTERNAL_LOAD.search(p.read_text()), f"{p} loads something external"


def test_the_page_reads_the_two_data_files_by_relative_path():
    text = (SITE / "app.js").read_text()
    assert "data/site-data.json" in text
    assert "data/oregon-counties.geojson" in text
    assert not re.search(r"""fetch\(\s*["'`]/""", text)  # root-relative would break on Pages
