"""Checks every committed records file, so a bad edit to real data fails CI.

Quote verification against the source PDFs is not done here because the PDFs are local only;
run ``uv run ofs validate <file> --pdf-dir <folder>`` for that.
"""

import pytest

from conftest import REPO_ROOT
from oregon_farmland_solar.dataset import check_dataset, load_dataset
from oregon_farmland_solar.pii import scan_dataset
from oregon_farmland_solar.taxonomy import load_taxonomy

RECORD_FILES = sorted((REPO_ROOT / "data" / "records").glob("*.json"))


@pytest.mark.parametrize("path", RECORD_FILES, ids=lambda p: p.name)
def test_committed_records_are_valid(path, taxonomy_path):
    ds = load_dataset(path)
    errors = [i for i in check_dataset(ds, load_taxonomy(taxonomy_path)) if i.level == "error"]
    assert errors == []
    assert scan_dataset(ds) == []


def test_there_are_record_files():
    assert RECORD_FILES
