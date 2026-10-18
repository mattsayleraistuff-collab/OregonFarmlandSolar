import re
from pathlib import Path

import pytest

from oregon_farmland_solar.taxonomy import TaxonomyError, load_taxonomy


def test_real_taxonomy_loads_and_has_catch_all(taxonomy_path):
    tax = load_taxonomy(taxonomy_path)
    assert tax.version
    assert "other_uncoded" in tax.ids()


def test_real_taxonomy_ids_are_snake_case_and_unique(taxonomy_path):
    tax = load_taxonomy(taxonomy_path)
    ids = [e.id for e in tax.entries]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"[a-z][a-z0-9_]*", i) for i in ids)


def test_every_entry_has_label_and_definition(taxonomy_path):
    tax = load_taxonomy(taxonomy_path)
    for entry in tax.entries:
        assert entry.label.strip()
        assert entry.definition.strip()


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "t.yaml"
    p.write_text(body)
    return p


def test_duplicate_ids_rejected(tmp_path):
    p = _write(
        tmp_path,
        """
version: 1
entries:
  - {id: a, label: A, definition: d, status: active}
  - {id: a, label: A2, definition: d, status: active}
  - {id: other_uncoded, label: Other, definition: d, status: active}
""",
    )
    with pytest.raises(TaxonomyError, match="duplicate"):
        load_taxonomy(p)


def test_deprecated_entry_must_point_to_existing_replacement(tmp_path):
    p = _write(
        tmp_path,
        """
version: 1
entries:
  - {id: old, label: Old, definition: d, status: deprecated, replaced_by: missing}
  - {id: other_uncoded, label: Other, definition: d, status: active}
""",
    )
    with pytest.raises(TaxonomyError, match="replaced_by"):
        load_taxonomy(p)


def test_missing_catch_all_rejected(tmp_path):
    p = _write(
        tmp_path,
        """
version: 1
entries:
  - {id: a, label: A, definition: d, status: active}
""",
    )
    with pytest.raises(TaxonomyError, match="other_uncoded"):
        load_taxonomy(p)


def test_active_ids_excludes_deprecated(tmp_path):
    p = _write(
        tmp_path,
        """
version: 1
entries:
  - {id: old, label: Old, definition: d, status: deprecated, replaced_by: new}
  - {id: new, label: New, definition: d, status: active}
  - {id: other_uncoded, label: Other, definition: d, status: active}
""",
    )
    tax = load_taxonomy(p)
    assert tax.active_ids() == {"new", "other_uncoded"}
    assert "old" in tax.ids()
