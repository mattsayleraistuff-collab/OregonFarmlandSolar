import pytest

from oregon_farmland_solar.dataset import Dataset
from oregon_farmland_solar.pii import scan_dataset, scan_text


@pytest.mark.parametrize(
    "text, kind",
    [
        ("Contact jane.doe@example.com for details", "email"),
        ("Call (503) 555-0142 before noon", "phone"),
        ("Call 503-555-0142", "phone"),
        ("Call 503.555.0142", "phone"),
        ("SSN 123-45-6789 on file", "ssn"),
    ],
)
def test_detects_patterns(text, kind):
    assert kind in {f.kind for f in scan_text(text)}


def test_clean_text_has_no_findings():
    assert scan_text("The 12-acre facility was denied on 2018-01-25 under ORS 215.447.") == []


def test_blocklist_terms_are_case_insensitive():
    findings = scan_text("Owner John Q. Public objected", blocklist=["john q. public"])
    assert [f.kind for f in findings] == ["blocklist"]


def test_scan_dataset_reports_reason_ids(raw_dataset):
    raw_dataset["reasons"][0]["quote"] = "Reach the owner at owner@example.com"
    findings = scan_dataset(Dataset.model_validate(raw_dataset))
    assert [(f.record_id, f.kind) for f in findings] == [("r1", "email")]


def test_scan_dataset_also_checks_notes(raw_dataset):
    raw_dataset["reasons"][0]["note"] = "phone 503-555-0142"
    findings = scan_dataset(Dataset.model_validate(raw_dataset))
    assert any(f.record_id == "r1" and f.kind == "phone" for f in findings)


@pytest.mark.parametrize(
    "text",
    [
        "criteria required by OAR 660-033-0130(38).",
        "see OAR 660-006-0025 for forest uses",
        "under 660-033-0130(38)(h)",
    ],
)
def test_oar_rule_numbers_are_not_phone_numbers(text):
    assert scan_text(text) == []
