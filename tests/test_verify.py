import hashlib

from oregon_farmland_solar.dataset import Dataset
from oregon_farmland_solar.verify import index_pdfs, verify_quotes

SHA = "a" * 64
PAGES = ["page one text", "The county found the facility would harm adjacent vineyard operations."]


def _real(raw_dataset: dict) -> Dataset:
    for table in raw_dataset.values():
        for row in table:
            row["synthetic"] = False
    raw_dataset["documents"][0]["sha256"] = SHA
    raw_dataset["documents"][0]["page_count"] = 2
    raw_dataset["reasons"][0]["pdf_page"] = 2
    raw_dataset["reasons"][0]["quote"] = "would harm adjacent vineyard operations"
    return Dataset.model_validate(raw_dataset)


def test_quote_on_cited_page_passes(raw_dataset):
    assert verify_quotes(_real(raw_dataset), {SHA: PAGES}) == []


def test_quote_on_wrong_page_is_error(raw_dataset):
    ds = _real(raw_dataset)
    ds.reasons[0].pdf_page = 1
    issues = verify_quotes(ds, {SHA: PAGES})
    assert [i.level for i in issues] == ["error"]
    assert "r1" in issues[0].message


def test_missing_pdf_is_warning_not_error(raw_dataset):
    issues = verify_quotes(_real(raw_dataset), {})
    assert [i.level for i in issues] == ["warning"]


def test_page_count_mismatch_is_error(raw_dataset):
    issues = verify_quotes(_real(raw_dataset), {SHA: PAGES + ["extra"]})
    assert any(i.level == "error" and "page_count" in i.message for i in issues)


def test_synthetic_records_are_skipped(raw_dataset):
    ds = Dataset.model_validate(raw_dataset)
    assert verify_quotes(ds, {}) == []


def test_fuzzy_match_is_warning(raw_dataset):
    ds = _real(raw_dataset)
    ds.reasons[0].quote = "would harm adjacent vineyard operatlons"
    issues = verify_quotes(ds, {SHA: PAGES})
    assert [i.level for i in issues] == ["warning"]


def test_index_pdfs_keys_by_sha256(tmp_path):
    (tmp_path / "sub").mkdir()
    f = tmp_path / "sub" / "a.pdf"
    f.write_bytes(b"fake pdf bytes")
    idx = index_pdfs(tmp_path, extract=lambda p: ["p1", "p2"])
    assert idx == {hashlib.sha256(b"fake pdf bytes").hexdigest(): ["p1", "p2"]}
