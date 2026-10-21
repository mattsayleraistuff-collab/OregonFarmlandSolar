"""Command line entry point: `uv run ofs validate|synth|counties|site-data|stage-site|extract`."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path

from . import extract, geo, publish, site_data
from .dataset import Issue, check_dataset, load_dataset
from .pii import scan_dataset
from .synthetic import DEFAULT_COUNT, DEFAULT_SEED, generate
from .taxonomy import load_taxonomy
from .verify import extract_pages, index_pdfs, verify_quotes

DEFAULT_TAXONOMY = Path("data/taxonomy/reasons.yaml")
DEFAULT_SYNTH_OUT = Path("data/synthetic/synthetic-county-approvals.json")
DEFAULT_PROMPT = Path("prompts/extract-reasons-v1.txt")
DEFAULT_EXTRACT_OUT = Path("data/local/extract")


def _validate(args: argparse.Namespace) -> int:
    """Runs all checks on a records file and prints the issues.

    Args:
        args: Parsed arguments with ``records``, ``taxonomy``, ``pdf_dir`` and ``blocklist``.

    Returns:
        0 if there are no errors (warnings are allowed), otherwise 1.
    """
    ds = load_dataset(args.records)
    issues: list[Issue] = check_dataset(ds, load_taxonomy(args.taxonomy))

    blocklist: list[str] = []
    if args.blocklist:
        lines = Path(args.blocklist).read_text(encoding="utf-8").splitlines()
        blocklist = [ln.strip() for ln in lines if ln.strip()]
    for f in scan_dataset(ds, blocklist):
        issues.append(
            Issue("error", f"possible personal info ({f.kind}) in {f.record_id}: {f.match!r}")
        )

    if args.pdf_dir:
        issues += verify_quotes(ds, index_pdfs(Path(args.pdf_dir)))

    for i in issues:
        print(f"{i.level.upper()}: {i.message}")
    errors = sum(i.level == "error" for i in issues)
    if errors:
        print(f"{errors} error(s)")
        return 1
    print(f"OK ({len(ds.reasons)} reasons, {len(issues)} warning(s))")
    return 0


def _synth(args: argparse.Namespace) -> int:
    """Writes a synthetic records file.

    Args:
        args: Parsed arguments with ``seed``, ``count`` and ``out``.

    Returns:
        0 on success.
    """
    data = generate(args.seed, args.count)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(data['projects'])} synthetic projects to {out}")
    return 0


def _counties(args: argparse.Namespace) -> int:
    """Builds the Oregon county boundary layer from the BLM feature service.

    Args:
        args: Parsed arguments with ``out_dir`` and ``raw_dir``.

    Returns:
        0 on success.
    """
    prov = geo.build_counties(geo.fetch_layer, Path(args.out_dir), Path(args.raw_dir), date.today())
    print(
        f"Wrote {prov['feature_count_derived']} Oregon counties to {args.out_dir} "
        f"(raw sha256 {prov['raw_sha256'][:12]}...)"
    )
    return 0


def _simplify_counties(args: argparse.Namespace) -> int:
    """Simplifies the county geometry for the web and updates the provenance file.

    Args:
        args: Parsed arguments with ``percent``, ``out_dir`` and ``raw_dir``.

    Returns:
        0 on success.
    """
    prov = geo.simplify_counties(Path(args.out_dir), Path(args.raw_dir), args.percent)
    print(
        f"Simplified to {args.percent:g}% with mapshaper {geo.MAPSHAPER_VERSION}; "
        f"derived sha256 {prov['derived_sha256'][:12]}..."
    )
    return 0


def _site_data(args: argparse.Namespace) -> int:
    """Builds the JSON file the website reads from the real and synthetic records.

    Args:
        args: Parsed arguments with ``records_dir``, ``synthetic``, ``taxonomy`` and ``out``.

    Returns:
        0 on success.
    """
    real = site_data.load_merged(sorted(Path(args.records_dir).glob("*.json")))
    synth = site_data.load_merged([Path(args.synthetic)])
    data = site_data.build_site_data(real, synth, load_taxonomy(args.taxonomy))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"Wrote {data['real']['n_projects']} real and {data['synthetic']['n_projects']} "
        f"synthetic projects to {out}"
    )
    return 0


def _git_commit() -> str:
    """Returns the current git commit, with "-dirty" if there are uncommitted changes."""
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return head + ("-dirty" if dirty else "")


def _parse_pages(spec: str | None, count: int) -> list[int]:
    """Turns "3" or "2-5" or "1,4" into sorted 1-based page numbers within the document."""
    if not spec:
        return list(range(1, count + 1))
    pages: set[int] = set()
    for part in spec.split(","):
        lo, _, hi = part.partition("-")
        pages.update(range(int(lo), int(hi or lo) + 1))
    return sorted(p for p in pages if 1 <= p <= count)


def _extract(args: argparse.Namespace) -> int:
    """Runs the local model over one PDF and writes candidate reasons and a run manifest.

    Args:
        args: Parsed arguments (see ``main``).

    Returns:
        0 on success, 1 if the model or server is refused.
    """
    try:
        extract.check_host(args.host)
        confirm = input if sys.stdin.isatty() else None
        model = extract.check_model(
            args.model,
            extract.list_models(args.host),
            allow_cloud=args.allow_cloud,
            confirm=confirm,
        )
    except extract.LocalOnlyError as e:
        print(f"ERROR: {e}")
        return 1
    pdf = Path(args.pdf)
    all_pages = extract_pages(pdf)
    wanted = _parse_pages(args.pages, len(all_pages))
    prompt_text, prompt_sha = extract.load_prompt(Path(args.prompt))
    # Unselected pages stay in place as blanks so page numbers and ids stay true to the PDF.
    pages = [t if n in wanted else "" for n, t in enumerate(all_pages, start=1)]
    res = extract.run_document(
        doc_id=args.doc_id,
        pdf_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),
        pages=pages,
        prompt_text=prompt_text,
        model=model,
        send=extract.make_sender(args.host),
        temperature=args.temperature,
        seed=args.seed,
    )
    manifest = extract.build_manifest(
        res,
        pipeline_commit=_git_commit(),
        prompt_sha256=prompt_sha,
        model=model,
        temperature=args.temperature,
        seed=args.seed,
        host=args.host,
        cloud=extract.is_cloud(model),
        run_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{args.doc_id}.candidates.json").write_text(
        json.dumps(extract.output_document(res), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out / f"{args.doc_id}.manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    c = manifest["counts"]
    print(
        f"{c['accepted']} accepted, {c['review']} to review, {c['rejected']} rejected, "
        f"{c['page_errors']} page error(s); wrote {out}/{args.doc_id}.*.json"
    )
    return 0


def _stage_site(args: argparse.Namespace) -> int:
    """Builds the folder that is published to GitHub Pages.

    Args:
        args: Parsed arguments with ``site_dir``, ``geo`` and ``out``.

    Returns:
        0 on success.
    """
    publish.stage_site(Path(args.site_dir), Path(args.geo), Path(args.out))
    print(f"Staged the site in {args.out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Command line entry point.

    Args:
        argv: Arguments without the program name; defaults to ``sys.argv[1:]``.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(prog="ofs")
    sub = parser.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate", help="check a records file")
    v.add_argument("records")
    v.add_argument("--taxonomy", default=str(DEFAULT_TAXONOMY))
    v.add_argument("--pdf-dir", help="local folder of source PDFs; verifies quotes if given")
    v.add_argument("--blocklist", help="local text file of names/terms to flag, one per line")
    v.set_defaults(func=_validate)
    s = sub.add_parser("synth", help="write seeded synthetic demo records")
    s.add_argument("--seed", type=int, default=DEFAULT_SEED)
    s.add_argument("--count", type=int, default=DEFAULT_COUNT)
    s.add_argument("--out", default=str(DEFAULT_SYNTH_OUT))
    s.set_defaults(func=_synth)
    c = sub.add_parser("counties", help="download and build the Oregon county boundary layer")
    c.add_argument("--out-dir", default="data/geo")
    c.add_argument("--raw-dir", default="data/raw/geo")
    c.set_defaults(func=_counties)
    sc = sub.add_parser(
        "simplify-counties", help="simplify the county layer for the web (needs Node.js)"
    )
    sc.add_argument("--percent", type=float, default=5)
    sc.add_argument("--out-dir", default="data/geo")
    sc.add_argument("--raw-dir", default="data/raw/geo")
    sc.set_defaults(func=_simplify_counties)
    sd = sub.add_parser("site-data", help="build the JSON the website reads")
    sd.add_argument("--records-dir", default="data/records")
    sd.add_argument("--synthetic", default=str(DEFAULT_SYNTH_OUT))
    sd.add_argument("--taxonomy", default=str(DEFAULT_TAXONOMY))
    sd.add_argument("--out", default="site/data/site-data.json")
    sd.set_defaults(func=_site_data)
    ex = sub.add_parser("extract", help="propose reasons from a PDF with a local model")
    ex.add_argument("pdf")
    ex.add_argument("--doc-id", required=True, help="document id used in reason ids")
    ex.add_argument("--pages", help="only these pages, e.g. 23 or 20-25 or 1,4")
    ex.add_argument("--prompt", default=str(DEFAULT_PROMPT))
    ex.add_argument("--model", default=extract.DEFAULT_MODEL)
    ex.add_argument("--host", default=extract.DEFAULT_HOST)
    ex.add_argument("--temperature", type=float, default=extract.DEFAULT_TEMPERATURE)
    ex.add_argument("--seed", type=int, default=extract.DEFAULT_SEED)
    ex.add_argument(
        "--allow-cloud",
        action="store_true",
        help="allow a cloud model without asking (you accept responsibility for personal info)",
    )
    ex.add_argument("--out-dir", default=str(DEFAULT_EXTRACT_OUT))
    ex.set_defaults(func=_extract)
    st = sub.add_parser("stage-site", help="stage the static site for GitHub Pages")
    st.add_argument("--site-dir", default="site")
    st.add_argument("--geo", default="data/geo/oregon-counties.geojson")
    st.add_argument("--out", default="_site")
    st.set_defaults(func=_stage_site)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
