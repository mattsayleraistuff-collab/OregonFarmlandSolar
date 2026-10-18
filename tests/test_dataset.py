import copy

import pytest
from pydantic import ValidationError

from oregon_farmland_solar.dataset import Dataset, check_dataset
from oregon_farmland_solar.taxonomy import load_taxonomy


def _errors(raw, taxonomy_path):
    issues = check_dataset(Dataset.model_validate(raw), load_taxonomy(taxonomy_path))
    return [i.message for i in issues if i.level == "error"]


def _warnings(raw, taxonomy_path):
    issues = check_dataset(Dataset.model_validate(raw), load_taxonomy(taxonomy_path))
    return [i.message for i in issues if i.level == "warning"]


def test_valid_dataset_has_no_errors(raw_dataset, taxonomy_path):
    assert _errors(raw_dataset, taxonomy_path) == []


def test_local_proceeding_requires_local_outcome(raw_dataset):
    del raw_dataset["proceedings"][0]["local_outcome"]
    with pytest.raises(ValidationError):
        Dataset.model_validate(raw_dataset)


def test_local_proceeding_rejects_appeal_outcome(raw_dataset):
    raw_dataset["proceedings"][0]["appeal_outcome"] = "affirmed"
    with pytest.raises(ValidationError):
        Dataset.model_validate(raw_dataset)


def test_appeal_proceeding_requires_appeal_outcome(raw_dataset):
    del raw_dataset["proceedings"][1]["appeal_outcome"]
    with pytest.raises(ValidationError):
        Dataset.model_validate(raw_dataset)


def test_appeal_proceeding_rejects_local_outcome(raw_dataset):
    raw_dataset["proceedings"][1]["local_outcome"] = "denied"
    with pytest.raises(ValidationError):
        Dataset.model_validate(raw_dataset)


def test_unknown_outcome_value_rejected(raw_dataset):
    raw_dataset["proceedings"][0]["local_outcome"] = "maybe"
    with pytest.raises(ValidationError):
        Dataset.model_validate(raw_dataset)


def test_unknown_category_is_error(raw_dataset, taxonomy_path):
    raw_dataset["reasons"][0]["category"] = "not_a_real_reason"
    errs = _errors(raw_dataset, taxonomy_path)
    assert any("not_a_real_reason" in e for e in errs)


def test_other_uncoded_requires_note(raw_dataset, taxonomy_path):
    raw_dataset["reasons"][0]["category"] = "other_uncoded"
    assert any("note" in e for e in _errors(raw_dataset, taxonomy_path))
    raw_dataset["reasons"][0]["note"] = "Neighbor objected to glare."
    assert _errors(raw_dataset, taxonomy_path) == []


def test_reason_must_reference_existing_proceeding_and_document(raw_dataset, taxonomy_path):
    bad = copy.deepcopy(raw_dataset)
    bad["reasons"][0]["proceeding_id"] = "nope"
    assert any("nope" in e for e in _errors(bad, taxonomy_path))
    bad = copy.deepcopy(raw_dataset)
    bad["reasons"][0]["document_id"] = "nope"
    assert any("nope" in e for e in _errors(bad, taxonomy_path))


def test_reason_document_must_belong_to_reason_proceeding(raw_dataset, taxonomy_path):
    raw_dataset["reasons"][0]["document_id"] = "d-luba"  # belongs to pr-appeal
    assert any("belongs to" in e for e in _errors(raw_dataset, taxonomy_path))


def test_reasons_only_on_reason_bearing_documents(raw_dataset, taxonomy_path):
    raw_dataset["documents"][0]["document_type"] = "legal_digest"
    assert any("reason-bearing" in e for e in _errors(raw_dataset, taxonomy_path))


def test_duplicate_ids_are_errors(raw_dataset, taxonomy_path):
    raw_dataset["projects"].append(copy.deepcopy(raw_dataset["projects"][0]))
    assert any("duplicate" in e for e in _errors(raw_dataset, taxonomy_path))


def test_synthetic_flag_must_match_parent(raw_dataset, taxonomy_path):
    raw_dataset["reasons"][0]["synthetic"] = False
    assert any("synthetic" in e for e in _errors(raw_dataset, taxonomy_path))


def test_real_document_requires_sha256(raw_dataset, taxonomy_path):
    for table in ("projects", "proceedings", "documents", "reasons"):
        for row in raw_dataset[table]:
            row["synthetic"] = False
    assert any("sha256" in e for e in _errors(raw_dataset, taxonomy_path))
    for doc in raw_dataset["documents"]:
        doc["sha256"] = "a" * 64
    assert _errors(raw_dataset, taxonomy_path) == []


def test_bad_sha256_rejected(raw_dataset):
    raw_dataset["documents"][0]["sha256"] = "xyz"
    with pytest.raises(ValidationError):
        Dataset.model_validate(raw_dataset)


def test_deprecated_category_is_warning_not_error(raw_dataset, tmp_path):
    tax = tmp_path / "t.yaml"
    tax.write_text(
        """
version: 1
entries:
  - {id: neighbor_farm_impacts, label: N, definition: d, status: deprecated,
     replaced_by: other_uncoded}
  - {id: other_uncoded, label: Other, definition: d, status: active}
"""
    )
    assert _errors(raw_dataset, tax) == []
    assert any("deprecated" in w for w in _warnings(raw_dataset, tax))
