import json

from oregon_farmland_solar.cli import main


def test_valid_synthetic_dataset_exits_zero(tmp_path, raw_dataset, taxonomy_path, capsys):
    f = tmp_path / "d.json"
    f.write_text(json.dumps(raw_dataset))
    assert main(["validate", str(f), "--taxonomy", str(taxonomy_path)]) == 0
    assert "OK" in capsys.readouterr().out


def test_bad_category_exits_nonzero(tmp_path, raw_dataset, taxonomy_path, capsys):
    raw_dataset["reasons"][0]["category"] = "nope"
    f = tmp_path / "d.json"
    f.write_text(json.dumps(raw_dataset))
    assert main(["validate", str(f), "--taxonomy", str(taxonomy_path)]) == 1
    assert "nope" in capsys.readouterr().out


def test_pii_finding_exits_nonzero(tmp_path, raw_dataset, taxonomy_path):
    raw_dataset["reasons"][0]["quote"] = "email a@b.com"
    f = tmp_path / "d.json"
    f.write_text(json.dumps(raw_dataset))
    assert main(["validate", str(f), "--taxonomy", str(taxonomy_path)]) == 1
