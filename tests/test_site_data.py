"""Tests for the site data layer: records in, per-county and per-case JSON out."""

import json

import pytest

from conftest import REPO_ROOT
from oregon_farmland_solar import site_data
from oregon_farmland_solar.cli import main
from oregon_farmland_solar.dataset import Dataset
from oregon_farmland_solar.synthetic import generate
from oregon_farmland_solar.taxonomy import load_taxonomy

SHA = "a" * 64
COMMITTED = REPO_ROOT / "site" / "data" / "site-data.json"


def _real_raw() -> dict:
    """Two real LUBA-source projects: a Marion denial and a Jackson approval reversed twice."""

    def proj(pid, name, county):
        return {"id": pid, "name": name, "county": county, "source_type": "luba", "acres": 10}

    def proc(i, pid, level, **kw):
        return {"id": i, "project_id": pid, "level": level, "body": "Body", **kw}

    def doc(i, pr, dtype="appellate_opinion"):
        return {
            "id": i,
            "proceeding_id": pr,
            "document_type": dtype,
            "sha256": SHA,
            "file_name": f"{i}.pdf",
            "page_count": 30,
        }

    def reason(i, pr, d, cat, page, **kw):
        return {
            "id": i,
            "proceeding_id": pr,
            "document_id": d,
            "category": cat,
            "quote": f"Quote for {i}.",
            "pdf_page": page,
            **kw,
        }

    return {
        "projects": [proj("m", "Marion Test", "Marion"), proj("j", "Jackson Test", "Jackson")],
        "proceedings": [
            proc("m-local", "m", "local", local_outcome="denied", decision_date="2022-01-05"),
            proc("m-luba", "m", "appeal", appeal_outcome="affirmed", decision_date="2023-09-21"),
            proc(
                "j-local",
                "j",
                "local",
                local_outcome="approved_with_conditions",
                decision_date="2017-06-14",
            ),
            proc("j-2019", "j", "appeal", appeal_outcome="reversed", decision_date="2019-12-05"),
            proc("j-2017", "j", "appeal", appeal_outcome="reversed", decision_date="2017-10-27"),
        ],
        "documents": [
            doc("m-doc", "m-luba"),
            doc("j-doc-2017", "j-2017"),
            doc("j-doc-2019", "j-2019"),
        ],
        "reasons": [
            reason("m-r1", "m-local", "m-doc", "no_local_authority", 9, hand_checked=True),
            reason("m-r2", "m-luba", "m-doc", "state_farmland_standards", 4),
            reason("j-r1", "j-local", "j-doc-2017", "goal_exception_criteria", 24),
            reason("j-r2", "j-2017", "j-doc-2017", "goal_exception_criteria", 17),
            reason("j-r3", "j-2019", "j-doc-2019", "goal_exception_criteria", 5),
        ],
    }


@pytest.fixture
def taxonomy(taxonomy_path):
    return load_taxonomy(taxonomy_path)


@pytest.fixture
def built(taxonomy):
    real = Dataset.model_validate(_real_raw())
    synth = Dataset.model_validate(generate(1, 20))
    return site_data.build_site_data(real, synth, taxonomy)


def test_real_and_synthetic_are_separate_sections(built):
    assert set(built) == {"meta", "real", "synthetic"}
    assert built["real"]["n_projects"] == 2
    assert built["synthetic"]["n_projects"] == 20
    assert not any(p["synthetic"] for p in built["real"]["projects"])
    assert all(p["synthetic"] for p in built["synthetic"]["projects"])


def test_source_types_are_never_pooled(built):
    assert set(built["real"]["source_types"]) == {"luba"}
    assert set(built["synthetic"]["source_types"]) == {"county"}


def test_by_county_is_keyed_by_fips(built):
    by_county = built["real"]["source_types"]["luba"]["by_county"]
    assert set(by_county) == {"41047", "41029"}
    assert by_county["41047"]["name"] == "Marion"
    assert by_county["41047"]["county_outcomes"]["denied"] == 1
    assert by_county["41029"]["county_outcomes"]["approved_with_conditions"] == 1


def test_project_row_uses_the_local_outcome_and_latest_appeal(built):
    rows = {p["id"]: p for p in built["real"]["projects"]}
    assert rows["m"]["county_outcome"] == "denied"
    assert rows["m"]["appeal_outcome"] == "affirmed"
    assert rows["j"]["appeal_count"] == 2
    assert rows["j"]["fips"] == "41029"
    assert rows["j"]["reason_count"] == 3


def test_outcome_tallies_include_every_value_even_when_zero(built):
    block = built["real"]["source_types"]["luba"]
    assert block["county_outcomes"] == {
        "approved": 0,
        "approved_with_conditions": 1,
        "denied": 1,
    }
    assert block["appeal_outcomes"]["affirmed"] == 1
    assert block["appeal_outcomes"]["reversed"] == 1
    assert block["appeal_outcomes"]["remanded"] == 0
    assert block["appeal_outcomes"]["none"] == 0


def test_category_counts_have_labels_and_split_by_level(built, taxonomy):
    cats = {c["id"]: c for c in built["real"]["source_types"]["luba"]["categories"]}
    assert set(cats) == taxonomy.active_ids()
    goal = cats["goal_exception_criteria"]
    assert goal["count"] == 3
    assert goal["local"] == 1
    assert goal["appeal"] == 2
    assert goal["label"] == taxonomy.get("goal_exception_criteria").label
    assert cats["neighbor_farm_impacts"]["count"] == 0


def test_hand_checked_totals(built):
    block = built["real"]["source_types"]["luba"]
    assert block["reasons"] == 5
    assert block["hand_checked"] == 1


def test_cases_exist_only_for_real_data(built):
    assert len(built["real"]["cases"]) == 2
    assert "cases" not in built["synthetic"]


def test_case_orders_proceedings_local_first_then_appeals_by_date(built):
    case = {c["project"]["id"]: c for c in built["real"]["cases"]}["j"]
    assert [p["id"] for p in case["proceedings"]] == ["j-local", "j-2017", "j-2019"]
    assert case["proceedings"][1]["outcome"] == "reversed"


def test_case_reasons_carry_quote_page_document_and_label(built):
    case = {c["project"]["id"]: c for c in built["real"]["cases"]}["m"]
    reason = case["proceedings"][0]["reasons"][0]
    assert reason["quote"] == "Quote for m-r1."
    assert reason["pdf_page"] == 9
    assert reason["document_id"] == "m-doc"
    assert reason["hand_checked"] is True
    assert reason["label"] == "No local code authority for the use"


def test_case_reasons_are_sorted_by_document_then_page(built):
    case = {c["project"]["id"]: c for c in built["real"]["cases"]}["j"]
    local = case["proceedings"][0]["reasons"]
    pages = [(r["document_id"], r["pdf_page"]) for r in local]
    assert pages == sorted(pages)


def test_case_lists_its_documents(built):
    case = {c["project"]["id"]: c for c in built["real"]["cases"]}["j"]
    assert {d["id"] for d in case["documents"]} == {"j-doc-2017", "j-doc-2019"}
    assert case["documents"][0]["sha256"] == SHA


def test_meta_carries_the_required_result_labels_and_synthetic_notice(built):
    meta = built["meta"]
    assert meta["labels"]["county_outcome"] == "county outcome"
    assert meta["labels"]["appeal_outcome"] == "appeal outcome (where in our records)"
    assert "synthetic" in meta["synthetic_notice"].lower()


def test_build_is_deterministic(taxonomy):
    a = site_data.build_site_data(
        Dataset.model_validate(_real_raw()), Dataset.model_validate(generate(1, 20)), taxonomy
    )
    b = site_data.build_site_data(
        Dataset.model_validate(_real_raw()), Dataset.model_validate(generate(1, 20)), taxonomy
    )
    assert json.dumps(a, sort_keys=False) == json.dumps(b, sort_keys=False)


def test_unknown_county_is_an_error(taxonomy):
    raw = _real_raw()
    raw["projects"][0]["county"] = "Atlantis"
    with pytest.raises(ValueError, match="Atlantis"):
        site_data.build_site_data(
            Dataset.model_validate(raw), Dataset.model_validate(generate(1, 5)), taxonomy
        )


def test_synthetic_record_in_the_real_dataset_is_an_error(taxonomy):
    with pytest.raises(ValueError, match="synthetic"):
        site_data.build_site_data(
            Dataset.model_validate(generate(1, 5)), Dataset.model_validate(generate(2, 5)), taxonomy
        )


def test_real_record_in_the_synthetic_dataset_is_an_error(taxonomy):
    with pytest.raises(ValueError, match="synthetic"):
        site_data.build_site_data(
            Dataset.model_validate(_real_raw()), Dataset.model_validate(_real_raw()), taxonomy
        )


def test_personal_information_in_a_quote_is_an_error(taxonomy):
    raw = _real_raw()
    raw["reasons"][0]["quote"] = "Call 541-555-0123 for details."
    with pytest.raises(ValueError, match="personal"):
        site_data.build_site_data(
            Dataset.model_validate(raw), Dataset.model_validate(generate(1, 5)), taxonomy
        )


def test_dataset_errors_stop_the_build(taxonomy):
    raw = _real_raw()
    raw["reasons"][0]["category"] = "nope"
    with pytest.raises(ValueError, match="nope"):
        site_data.build_site_data(
            Dataset.model_validate(raw), Dataset.model_validate(generate(1, 5)), taxonomy
        )


def test_load_merged_combines_record_files(tmp_path):
    a = _real_raw()
    b = {"projects": [], "proceedings": [], "documents": [], "reasons": []}
    (tmp_path / "a.json").write_text(json.dumps(a))
    (tmp_path / "b.json").write_text(json.dumps(b))
    ds = site_data.load_merged(sorted(tmp_path.glob("*.json")))
    assert len(ds.projects) == 2


def test_cli_site_data_writes_the_file(tmp_path, taxonomy_path):
    rec = tmp_path / "records"
    rec.mkdir()
    (rec / "real.json").write_text(json.dumps(_real_raw()))
    synth = tmp_path / "synth.json"
    synth.write_text(json.dumps(generate(1, 10)))
    out = tmp_path / "site" / "data" / "site-data.json"
    code = main(
        [
            "site-data",
            "--records-dir",
            str(rec),
            "--synthetic",
            str(synth),
            "--taxonomy",
            str(taxonomy_path),
            "--out",
            str(out),
        ]
    )
    assert code == 0
    assert json.loads(out.read_text())["real"]["n_projects"] == 2


@pytest.mark.skipif(not COMMITTED.exists(), reason="site data not built yet")
def test_committed_site_data_matches_the_committed_records(taxonomy):
    real = site_data.load_merged(sorted((REPO_ROOT / "data" / "records").glob("*.json")))
    synth = site_data.load_merged(
        [REPO_ROOT / "data" / "synthetic" / "synthetic-county-approvals.json"]
    )
    expected = site_data.build_site_data(real, synth, taxonomy)
    assert json.loads(COMMITTED.read_text()) == expected
