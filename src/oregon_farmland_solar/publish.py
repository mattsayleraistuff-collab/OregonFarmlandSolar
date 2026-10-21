"""Stages the static website for GitHub Pages.

The staged folder holds only the files the site needs: the files under ``site/`` plus the
county boundary layer. Nothing else can get in: files of types that should never be published
(PDFs, environment files, keys, code) and hidden files make the build fail, so source
documents or secrets cannot reach the public site by accident.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ALLOWED_SUFFIXES = frozenset(
    {
        ".html",
        ".css",
        ".js",
        ".json",
        ".geojson",
        ".svg",
        ".png",
        ".jpg",
        ".ico",
        ".woff2",
        ".txt",
        ".webmanifest",
    }
)
GEO_TARGET = Path("data") / "oregon-counties.geojson"
REQUIRED = (Path("index.html"), Path("data") / "site-data.json")


def stage_site(site_dir: Path, geo_file: Path, out_dir: Path) -> None:
    """Copies the site and the county layer into ``out_dir``, which is replaced.

    Args:
        site_dir: The site folder (``site/``), holding ``index.html`` and ``data/site-data.json``.
        geo_file: The county boundary GeoJSON to publish as ``data/oregon-counties.geojson``.
        out_dir: Folder to build the publishable site in; deleted and recreated.

    Raises:
        FileNotFoundError: If the page, the site data or the county layer is missing.
        ValueError: If ``out_dir`` is inside ``site_dir``, or ``site_dir`` holds a hidden file
            or a file type that may not be published.
    """
    site_dir, geo_file, out_dir = Path(site_dir), Path(geo_file), Path(out_dir)
    for rel in REQUIRED:
        if not (site_dir / rel).is_file():
            raise FileNotFoundError(f"missing {rel.as_posix()} in {site_dir}")
    if not geo_file.is_file():
        raise FileNotFoundError(f"missing county layer {geo_file}")
    if out_dir.resolve().is_relative_to(site_dir.resolve()):
        raise ValueError("the output folder must not be inside the site folder")

    files = sorted(p for p in site_dir.rglob("*") if p.is_file())
    refused = [
        p.relative_to(site_dir).as_posix()
        for p in files
        if p.name.startswith(".") or p.suffix.lower() not in ALLOWED_SUFFIXES
    ]
    if refused:
        raise ValueError(f"files that may not be published: {refused}")

    if out_dir.exists():
        shutil.rmtree(out_dir)
    for p in files:
        dest = out_dir / p.relative_to(site_dir)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, dest)
    (out_dir / GEO_TARGET).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(geo_file, out_dir / GEO_TARGET)
