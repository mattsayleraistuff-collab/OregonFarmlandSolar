"""Command line entry point: `uv run ofs validate|synth|counties`."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from . import geo
from .dataset import Issue, check_dataset, load_dataset
from .pii import scan_dataset
from .synthetic import DEFAULT_COUNT, DEFAULT_SEED, generate
from .taxonomy import load_taxonomy
from .verify import index_pdfs, verify_quotes

DEFAULT_TAXONOMY = Path("data/taxonomy/reasons.yaml")
DEFAULT_SYNTH_OUT = Path("data/synthetic/synthetic-county-approvals.json")


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
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
