"""Builds the JSON the website reads: per-county counts, category counts and case files.

Real and synthetic records go to separate sections and are never added together. Inside each
section, results are grouped by source type (luba, county, ...) and never pooled across types.
The build refuses to run if the records fail the dataset checks, if a real dataset contains a
synthetic record (or the reverse), if a quote looks like personal information, or if a project
is in a county that is not one of the 36 Oregon counties.

The result is plain JSON-compatible data, so the static site needs no server and no build tools.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import date
from pathlib import Path
from typing import Any

from .dataset import Dataset, check_dataset, load_dataset
from .geo import OREGON_FIPS
from .models import AppealOutcome, Level, LocalOutcome, Proceeding, Project, Reason
from .pii import scan_dataset
from .taxonomy import Taxonomy

LABELS = {
    "county_outcome": "county outcome",
    "appeal_outcome": "appeal outcome (where in our records)",
}
SYNTHETIC_NOTICE = (
    "Synthetic demo data: invented records that show how the tool works. "
    "They are not real decisions and must not be read as findings."
)


def load_merged(paths: Iterable[Path]) -> Dataset:
    """Loads several records files and combines them into one dataset.

    Args:
        paths: Records JSON files.

    Returns:
        A Dataset holding all projects, proceedings, documents and reasons from the files.
    """
    merged = Dataset()
    for path in paths:
        ds = load_dataset(path)
        merged.projects += ds.projects
        merged.proceedings += ds.proceedings
        merged.documents += ds.documents
        merged.reasons += ds.reasons
    return merged


def build_site_data(real: Dataset, synthetic: Dataset, taxonomy: Taxonomy) -> dict[str, Any]:
    """Builds the website data from the real and synthetic records.

    Args:
        real: The real records (every record must have ``synthetic`` false).
        synthetic: The synthetic demo records (every record must have ``synthetic`` true).
        taxonomy: The reason taxonomy, used for category labels.

    Returns:
        A dict with ``meta`` (required labels and the synthetic notice), ``real`` (projects,
        per-source-type tallies and case files) and ``synthetic`` (the same without cases).

    Raises:
        ValueError: If a dataset fails the checks, the two are mixed, a quote looks like
            personal information, or a project's county is not an Oregon county.
    """
    _check(real, taxonomy, expect_synthetic=False)
    _check(synthetic, taxonomy, expect_synthetic=True)
    return {
        "meta": {"labels": dict(LABELS), "synthetic_notice": SYNTHETIC_NOTICE},
        "real": _section(real, taxonomy, with_cases=True),
        "synthetic": _section(synthetic, taxonomy, with_cases=False),
    }


def _check(ds: Dataset, taxonomy: Taxonomy, *, expect_synthetic: bool) -> None:
    """Raises ValueError unless the dataset is valid, clean and on the expected side."""
    name = "synthetic" if expect_synthetic else "real"
    records = ds.projects + ds.proceedings + ds.documents + ds.reasons
    wrong = [r.id for r in records if r.synthetic != expect_synthetic]
    if wrong:
        kind = (
            "real record in the synthetic" if expect_synthetic else "synthetic record in the real"
        )
        raise ValueError(f"{kind} dataset: {wrong[:3]}")
    errors = [i.message for i in check_dataset(ds, taxonomy) if i.level == "error"]
    if errors:
        raise ValueError(f"{name} dataset has errors: {errors[:3]}")
    findings = scan_dataset(ds)
    if findings:
        f = findings[0]
        raise ValueError(
            f"possible personal information ({f.kind}) in {name} record {f.record_id}: {f.match!r}"
        )


def _date_key(p: Proceeding) -> tuple[date, str]:
    """Sort key: decision date (unknown dates first), then id."""
    return (p.decision_date or date.min, p.id)


def _section(ds: Dataset, taxonomy: Taxonomy, *, with_cases: bool) -> dict[str, Any]:
    """Builds one section (all real or all synthetic records)."""
    procs_by_project: dict[str, list[Proceeding]] = defaultdict(list)
    for pr in ds.proceedings:
        procs_by_project[pr.project_id].append(pr)
    proc_by_id = {pr.id: pr for pr in ds.proceedings}
    reasons_by_proc: dict[str, list[Reason]] = defaultdict(list)
    for r in ds.reasons:
        reasons_by_proc[r.proceeding_id].append(r)

    projects = sorted(ds.projects, key=lambda p: p.id)
    rows = [_row(p, procs_by_project[p.id], reasons_by_proc) for p in projects]

    source_types: dict[str, Any] = {}
    for st in sorted({p.source_type.value for p in projects}):
        members = [p for p in projects if p.source_type.value == st]
        source_types[st] = _source_block(members, rows, procs_by_project, proc_by_id, ds, taxonomy)

    section: dict[str, Any] = {
        "n_projects": len(projects),
        "projects": rows,
        "source_types": source_types,
    }
    if with_cases:
        section["cases"] = [
            _case(p, row, procs_by_project[p.id], reasons_by_proc, ds, taxonomy)
            for p, row in zip(projects, rows, strict=True)
        ]
    return section


def _fips(project: Project) -> str:
    """Returns the county FIPS code, or raises if the county is not an Oregon county."""
    try:
        return OREGON_FIPS[project.county]
    except KeyError:
        raise ValueError(f"unknown county {project.county!r} for project {project.id!r}") from None


def _local_and_appeals(procs: Sequence[Proceeding]) -> tuple[Proceeding | None, list[Proceeding]]:
    """Splits a project's proceedings into the latest local one and its appeals by date."""
    local = sorted((p for p in procs if p.level is Level.LOCAL), key=_date_key)
    appeals = sorted((p for p in procs if p.level is Level.APPEAL), key=_date_key)
    return (local[-1] if local else None), appeals


def _row(
    p: Project, procs: Sequence[Proceeding], reasons_by_proc: dict[str, list[Reason]]
) -> dict[str, Any]:
    """Builds one flat project row."""
    local, appeals = _local_and_appeals(procs)
    return {
        "id": p.id,
        "name": p.name,
        "county": p.county,
        "fips": _fips(p),
        "source_type": p.source_type.value,
        "acres": p.acres,
        "land_class": p.land_class_as_stated,
        "dual_use": p.dual_use,
        "county_outcome": local.local_outcome.value if local and local.local_outcome else None,
        "county_decision_date": local.decision_date.isoformat()
        if local and local.decision_date
        else None,
        "appeal_outcome": appeals[-1].appeal_outcome.value
        if appeals and appeals[-1].appeal_outcome
        else None,
        "appeal_count": len(appeals),
        "reason_count": sum(len(reasons_by_proc[pr.id]) for pr in procs),
        "synthetic": p.synthetic,
    }


def _outcome_tally(rows: Sequence[dict[str, Any]]) -> tuple[dict[str, int], dict[str, int]]:
    """Counts county outcomes and (latest) appeal outcomes, with every value present."""
    county = {o.value: 0 for o in LocalOutcome}
    appeal = {o.value: 0 for o in AppealOutcome} | {"none": 0}
    for r in rows:
        if r["county_outcome"] is not None:
            county[r["county_outcome"]] += 1
        appeal[r["appeal_outcome"] or "none"] += 1
    return county, appeal


def _source_block(
    members: Sequence[Project],
    all_rows: Sequence[dict[str, Any]],
    procs_by_project: dict[str, list[Proceeding]],
    proc_by_id: dict[str, Proceeding],
    ds: Dataset,
    taxonomy: Taxonomy,
) -> dict[str, Any]:
    """Builds the tallies for the projects of one source type."""
    ids = {p.id for p in members}
    rows = [r for r in all_rows if r["id"] in ids]
    reasons = [r for r in ds.reasons if proc_by_id[r.proceeding_id].project_id in ids]
    county_o, appeal_o = _outcome_tally(rows)

    cats: dict[str, dict[str, int]] = {}
    for r in reasons:
        level = proc_by_id[r.proceeding_id].level.value
        c = cats.setdefault(r.category, {"count": 0, "local": 0, "appeal": 0})
        c["count"] += 1
        c[level] += 1
    categories = [
        {
            "id": e.id,
            "label": e.label,
            **cats.get(e.id, {"count": 0, "local": 0, "appeal": 0}),
        }
        for e in taxonomy.entries
        if e.status == "active" or e.id in cats
    ]

    by_county: dict[str, Any] = {}
    for fips in sorted({r["fips"] for r in rows}):
        in_county = [r for r in rows if r["fips"] == fips]
        c_o, a_o = _outcome_tally(in_county)
        county_ids = {r["id"] for r in in_county}
        counts: dict[str, int] = {}
        for rs in reasons:
            if proc_by_id[rs.proceeding_id].project_id in county_ids:
                counts[rs.category] = counts.get(rs.category, 0) + 1
        by_county[fips] = {
            "name": in_county[0]["county"],
            "n_projects": len(in_county),
            "county_outcomes": c_o,
            "appeal_outcomes": a_o,
            "categories": dict(sorted(counts.items())),
        }

    return {
        "n_projects": len(rows),
        "county_outcomes": county_o,
        "appeal_outcomes": appeal_o,
        "reasons": len(reasons),
        "hand_checked": sum(r.hand_checked for r in reasons),
        "categories": categories,
        "by_county": by_county,
    }


def _case(
    p: Project,
    row: dict[str, Any],
    procs: Sequence[Proceeding],
    reasons_by_proc: dict[str, list[Reason]],
    ds: Dataset,
    taxonomy: Taxonomy,
) -> dict[str, Any]:
    """Builds the case file for one real project: proceedings, their reasons and documents."""
    local, appeals = _local_and_appeals(procs)
    ordered = sorted((p for p in procs if p.level is Level.LOCAL), key=_date_key) + appeals
    proc_ids = {pr.id for pr in procs}
    docs = sorted((d for d in ds.documents if d.proceeding_id in proc_ids), key=lambda d: d.id)

    def reason_view(r: Reason) -> dict[str, Any]:
        entry = taxonomy.get(r.category)
        return {
            "id": r.id,
            "category": r.category,
            "label": entry.label if entry else r.category,
            "quote": r.quote,
            "document_id": r.document_id,
            "pdf_page": r.pdf_page,
            "printed_page": r.printed_page,
            "note": r.note,
            "hand_checked": r.hand_checked,
        }

    return {
        "project": row,
        "proceedings": [
            {
                "id": pr.id,
                "level": pr.level.value,
                "body": pr.body,
                "decision_date": pr.decision_date.isoformat() if pr.decision_date else None,
                "citation": pr.citation,
                "outcome": (pr.local_outcome or pr.appeal_outcome).value,
                "reasons": [
                    reason_view(r)
                    for r in sorted(
                        reasons_by_proc[pr.id], key=lambda r: (r.document_id, r.pdf_page, r.id)
                    )
                ],
            }
            for pr in ordered
        ],
        "documents": [
            {
                "id": d.id,
                "document_type": d.document_type.value,
                "file_name": d.file_name,
                "page_count": d.page_count,
                "sha256": d.sha256,
            }
            for d in docs
        ],
    }
