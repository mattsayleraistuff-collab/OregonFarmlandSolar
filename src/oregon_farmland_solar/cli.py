"""Command line entry point: `uv run ofs validate data/records/<file>.json`."""

from __future__ import annotations

import argparse
from pathlib import Path

from .dataset import Issue, check_dataset, load_dataset
from .pii import scan_dataset
from .taxonomy import load_taxonomy
from .verify import index_pdfs, verify_quotes

DEFAULT_TAXONOMY = Path("data/taxonomy/reasons.yaml")


def _validate(args: argparse.Namespace) -> int:
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ofs")
    sub = parser.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate", help="check a records file")
    v.add_argument("records")
    v.add_argument("--taxonomy", default=str(DEFAULT_TAXONOMY))
    v.add_argument("--pdf-dir", help="local folder of source PDFs; verifies quotes if given")
    v.add_argument("--blocklist", help="local text file of names/terms to flag, one per line")
    v.set_defaults(func=_validate)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
