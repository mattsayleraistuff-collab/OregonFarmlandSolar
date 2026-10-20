"""Tests for the synthetic demo data generator."""

import json

import pytest

from conftest import REPO_ROOT
from oregon_farmland_solar.cli import main
from oregon_farmland_solar.dataset import Dataset, check_dataset, load_dataset
from oregon_farmland_solar.models import Level, LocalOutcome, SourceType
from oregon_farmland_solar.pii import scan_dataset
from oregon_farmland_solar.synthetic import (
    DEFAULT_COUNT,
    DEFAULT_SEED,
    OREGON_COUNTIES,
    generate,
)
from oregon_farmland_solar.taxonomy import load_taxonomy

COMMITTED = REPO_ROOT / "data" / "synthetic" / "synthetic-county-approvals.json"


def _ds(seed=1, count=40) -> Dataset:
    return Dataset.model_validate(generate(seed, count))


def test_counties_are_the_36_oregon_counties():
    assert len(OREGON_COUNTIES) == 36
    assert len(set(OREGON_COUNTIES)) == 36


def test_same_seed_gives_identical_output():
    assert generate(7, 30) == generate(7, 30)


def test_different_seed_gives_different_output():
    assert generate(7, 30) != generate(8, 30)


def test_count_projects_are_generated():
    assert len(_ds(count=25).projects) == 25


def test_output_passes_dataset_checks(taxonomy_path):
    ds = _ds()
    errors = [i for i in check_dataset(ds, load_taxonomy(taxonomy_path)) if i.level == "error"]
    assert errors == []


def test_every_record_is_flagged_synthetic():
    ds = _ds()
    records = ds.projects + ds.proceedings + ds.documents + ds.reasons
    assert records
    assert all(r.synthetic for r in records)


def test_project_names_are_obviously_fictional():
    assert all(p.name.startswith("Synthetic ") for p in _ds().projects)


def test_county_records_are_approvals_only_with_no_appeals():
    ds = _ds(count=60)
    assert all(p.source_type is SourceType.COUNTY for p in ds.projects)
    assert all(pr.level is Level.LOCAL for pr in ds.proceedings)
    assert all(
        pr.local_outcome in {LocalOutcome.APPROVED, LocalOutcome.APPROVED_WITH_CONDITIONS}
        for pr in ds.proceedings
    )


def test_each_project_has_one_proceeding_and_a_reason():
    ds = _ds()
    for p in ds.projects:
        procs = [pr for pr in ds.proceedings if pr.project_id == p.id]
        assert len(procs) == 1
        assert any(r.proceeding_id == procs[0].id for r in ds.reasons)


def test_projects_are_spread_across_several_counties():
    assert len({p.county for p in _ds(count=60).projects}) >= 10


def test_quotes_are_marked_synthetic_and_never_look_like_real_text():
    assert all(r.quote.startswith("[SYNTHETIC]") for r in _ds().reasons)


def test_reasons_are_not_hand_checked():
    assert not any(r.hand_checked for r in _ds().reasons)


def test_output_has_no_personal_information_findings():
    assert scan_dataset(_ds(count=80)) == []


def test_reason_pages_fit_inside_the_document():
    ds = _ds()
    pages = {d.id: d.page_count for d in ds.documents}
    assert all(r.pdf_page <= pages[r.document_id] for r in ds.reasons)


def test_count_must_be_positive():
    with pytest.raises(ValueError):
        generate(1, 0)


def test_cli_writes_a_file_that_validates(tmp_path, taxonomy_path):
    out = tmp_path / "s.json"
    assert main(["synth", "--seed", "3", "--count", "10", "--out", str(out)]) == 0
    assert json.loads(out.read_text()) == generate(3, 10)
    assert main(["validate", str(out), "--taxonomy", str(taxonomy_path)]) == 0


def test_committed_file_matches_the_generator():
    """The committed demo file is exactly what the generator produces, so it is reproducible."""
    assert json.loads(COMMITTED.read_text()) == generate(DEFAULT_SEED, DEFAULT_COUNT)


def test_committed_file_is_valid(taxonomy_path):
    ds = load_dataset(COMMITTED)
    errors = [i for i in check_dataset(ds, load_taxonomy(taxonomy_path)) if i.level == "error"]
    assert errors == []
    assert scan_dataset(ds) == []
