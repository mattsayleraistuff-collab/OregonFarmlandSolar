"""Tests for comparing machine-proposed reasons with hand-coded ones."""

import json

import pytest

from oregon_farmland_solar import compare

Q1 = "The county further balances the Comprehensive Plan goals in favor of farmland protection"
Q2 = "There is no evidence in the record that the proposed solar facility would create a hazard"
Q3 = "LUBA concludes the findings are inadequate to explain why the exception criteria are met"


def hand(page, quote, rid="h1"):
    return {"id": rid, "pdf_page": page, "quote": quote, "category": "farmland_loss"}


def found(page, quote, rid="f1"):
    return {"id": rid, "pdf_page": page, "quote": quote}


def test_normalize_ignores_case_spacing_and_curly_quotes():
    assert compare.normalize("The  County’s\nPlan") == ["the", "county's", "plan"]


def test_overlap_is_the_share_of_the_shorter_quote_found_in_order():
    a = compare.normalize(Q1)
    assert compare.overlap(a, a) == 1.0
    longer = compare.normalize("Further, " + Q1 + " because a solar facility can be elsewhere")
    assert compare.overlap(a, longer) == 1.0
    assert compare.overlap(a, compare.normalize(Q2)) < 0.3
    assert compare.overlap([], a) == 0.0


def test_same_quote_on_the_same_page_is_a_match():
    c = compare.compare([hand(5, Q1)], [found(5, Q1)], scanned_pages=[5])
    assert len(c.matches) == 1
    assert c.matches[0].kind == "same"
    assert c.missed == [] and c.extras == []


def test_a_quote_that_covers_most_of_the_hand_quote_is_a_partial_match():
    longer = Q1 + " because a solar facility can be located on non-farmland and nearby"
    c = compare.compare([hand(5, Q1)], [found(5, longer)], scanned_pages=[5])
    assert c.matches[0].kind == "partial"


def test_a_quote_on_a_different_page_does_not_match():
    c = compare.compare([hand(5, Q1)], [found(6, Q1)], scanned_pages=[5, 6])
    assert c.matches == []
    assert [m.id for m in c.missed] == ["h1"]
    assert [e.found["id"] for e in c.extras] == ["f1"]


def test_each_quote_is_used_once():
    c = compare.compare(
        [hand(5, Q1, "h1"), hand(5, Q1, "h2")],
        [found(5, Q1)],
        scanned_pages=[5],
    )
    assert len(c.matches) == 1
    assert len(c.missed) == 1


def test_misses_on_pages_never_scanned_are_kept_apart():
    c = compare.compare([hand(5, Q1), hand(9, Q2, "h2")], [found(5, Q1)], scanned_pages=[5])
    assert c.missed == []
    assert [h["id"] for h in c.not_scanned] == ["h2"]
    assert c.recall == 1.0


def test_a_missed_reason_says_whether_the_gate_held_the_quote_back():
    held = [
        {"pdf_page": 9, "quote": Q2, "status": "review", "reason": "fuzzy match"},
        {"pdf_page": 12, "quote": Q3, "status": "rejected", "reason": "too short"},
    ]
    c = compare.compare(
        [hand(9, Q2, "h2"), hand(12, Q3, "h3"), hand(14, Q1, "h4")],
        [],
        scanned_pages=[9, 12, 14],
        held_back=held,
    )
    why = {m.hand["id"]: m.why for m in c.missed}
    assert why["h2"].startswith("held for review")
    assert why["h3"].startswith("rejected by the quote check")
    assert why["h4"] == "not proposed"


def test_extras_note_whether_the_page_has_a_hand_coded_reason():
    c = compare.compare(
        [hand(5, Q1)], [found(5, Q2, "f1"), found(8, Q3, "f2")], scanned_pages=[5, 8]
    )
    flags = {e.found["id"]: e.page_has_hand_coded for e in c.extras}
    assert flags == {"f1": True, "f2": False}


def test_recall_counts_only_hand_coded_reasons_on_scanned_pages():
    c = compare.compare(
        [hand(5, Q1), hand(6, Q2, "h2"), hand(7, Q3, "h3")],
        [found(5, Q1)],
        scanned_pages=[5, 6],
    )
    assert c.recall == 0.5
    assert compare.compare([], [], scanned_pages=[1]).recall is None


def test_the_report_states_what_the_numbers_do_and_do_not_mean():
    c = compare.compare([hand(5, Q1)], [found(5, Q1), found(6, Q2, "f2")], scanned_pages=[5, 6])
    md = compare.render_markdown(c, title="Yamhill", meta={"model": "m", "prompt_sha256": "p"})
    assert "# Yamhill" in md
    assert "1 of 1" in md
    assert "Extras are not necessarily errors" in md
    assert "model: m" in md
    assert Q2 in md


def test_cli_compare_writes_a_report_and_a_json_summary(tmp_path):
    from oregon_farmland_solar.cli import main

    records = tmp_path / "records.json"
    records.write_text(
        json.dumps(
            {
                "reasons": [
                    {**hand(5, Q1), "document_id": "doc-a"},
                    {**hand(6, Q2, "h2"), "document_id": "doc-b"},
                ]
            }
        )
    )
    cand = tmp_path / "x.candidates.json"
    cand.write_text(
        json.dumps(
            {
                "document_id": "x",
                "reasons": [{"id": "x-p5-r1", "pdf_page": 5, "quote": Q1}],
                "needs_review": [],
                "rejected": [],
                "page_errors": [],
            }
        )
    )
    (tmp_path / "x.manifest.json").write_text(
        json.dumps(
            {
                "pipeline_commit": "abc",
                "prompt_sha256": "p" * 64,
                "model": {"name": "m", "digest": "d"},
                "settings": {"temperature": 0, "seed": 42},
                "input": {"scanned_pages": [5]},
            }
        )
    )
    out = tmp_path / "out"
    args = ["compare", str(cand), "--records", str(records), "--document", "doc-a"]
    assert main([*args, "--out-dir", str(out)]) == 0
    summary = json.loads((out / "x.comparison.json").read_text())
    assert summary["hand_coded"] == 1
    assert summary["matched"] == 1
    assert summary["records_sha256"] and summary["candidates_sha256"]
    assert (out / "x.comparison.md").read_text().startswith("# ")


def test_cli_compare_refuses_an_unknown_document(tmp_path, capsys):
    from oregon_farmland_solar.cli import main

    records = tmp_path / "r.json"
    records.write_text(json.dumps({"reasons": []}))
    cand = tmp_path / "x.candidates.json"
    cand.write_text(json.dumps({"document_id": "x", "reasons": []}))
    code = main(["compare", str(cand), "--records", str(records), "--document", "nope"])
    assert code == 1
    assert "nope" in capsys.readouterr().out


def test_missing_manifest_is_an_error_not_a_guess(tmp_path):
    cand = tmp_path / "x.candidates.json"
    cand.write_text("{}")
    with pytest.raises(FileNotFoundError):
        compare.manifest_path_for(cand, must_exist=True)
