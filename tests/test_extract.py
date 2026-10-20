"""Tests for the local-model extraction pipeline (no real model: the transport is injected)."""

import hashlib
import json

import pytest

from conftest import REPO_ROOT
from oregon_farmland_solar import extract
from oregon_farmland_solar.extract import (
    CloudModelRefused,
    LocalOnlyError,
    ModelInfo,
)

PAGE = (
    "12   The county finds that removing farmland from agricultural production and allowing\n"
    "13   heavy construction could adversely affect the long-term suitability of soil\n"
    "14   resources for agricultural uses in this zone.\n"
)
GOOD = "removing farmland from agricultural production and allowing heavy construction"
SHA = "b" * 64


def _reply(reasons, has=None) -> str:
    return json.dumps({"has_reasons": bool(reasons) if has is None else has, "reasons": reasons})


# ---- prompt file -------------------------------------------------------------------------


def test_prompt_is_loaded_with_its_hash(tmp_path):
    f = tmp_path / "p.txt"
    f.write_text("Hello\nPAGE TEXT:\n", encoding="utf-8")
    text, sha = extract.load_prompt(f)
    assert text == "Hello\nPAGE TEXT:\n"
    assert sha == hashlib.sha256(f.read_bytes()).hexdigest()


def test_the_committed_prompt_ends_with_the_page_text_marker():
    text, _ = extract.load_prompt(REPO_ROOT / "prompts" / "extract-reasons-v1.txt")
    assert text.rstrip().endswith("PAGE TEXT:")
    assert "word for word" in text


def test_build_prompt_appends_the_page():
    assert extract.build_prompt("A\nPAGE TEXT:\n", "page") == "A\nPAGE TEXT:\npage"


# ---- parsing -----------------------------------------------------------------------------


def test_parse_accepts_the_expected_shape():
    out = extract.parse_response(_reply([{"quote": GOOD, "source": "county"}]))
    assert out.has_reasons is True
    assert out.reasons == [extract.RawReason(quote=GOOD, source="county")]
    assert out.error is None


def test_parse_accepts_no_reasons():
    out = extract.parse_response('{"has_reasons": false, "reasons": []}')
    assert out.has_reasons is False
    assert out.reasons == []
    assert out.error is None


@pytest.mark.parametrize(
    "bad",
    [
        "not json",
        "[]",
        '{"reasons": []}',
        '{"has_reasons": "yes", "reasons": []}',
        '{"has_reasons": true, "reasons": [{"quote": "x"}]}',
        '{"has_reasons": true, "reasons": [{"quote": "x", "source": "judge"}]}',
        '{"has_reasons": true, "reasons": [{"quote": 5, "source": "county"}]}',
    ],
)
def test_parse_reports_malformed_output_instead_of_guessing(bad):
    out = extract.parse_response(bad)
    assert out.error
    assert out.reasons == []


def test_parse_flags_a_contradiction_between_flag_and_list():
    out = extract.parse_response(_reply([{"quote": GOOD, "source": "county"}], has=False))
    assert out.error


# ---- quote gate --------------------------------------------------------------------------


def test_gate_accepts_an_exact_quote():
    r = extract.RawReason(quote=GOOD, source="county")
    (g,) = extract.gate_quotes([r], PAGE)
    assert g.status == "accepted"
    assert g.score == 100.0


def test_gate_rejects_a_quote_that_is_not_on_the_page():
    r = extract.RawReason(
        quote="The project complies with the applicable land use regulations and zoning rules.",
        source="county",
    )
    (g,) = extract.gate_quotes([r], PAGE)
    assert g.status == "rejected"
    assert g.reason == "not_on_page"


def test_gate_sends_a_fuzzy_match_to_review_not_accepted():
    near = GOOD.replace("heavy", "heavvy")
    (g,) = extract.gate_quotes([extract.RawReason(quote=near, source="county")], PAGE)
    assert g.status == "review"
    assert g.reason == "fuzzy_match"


@pytest.mark.parametrize("quote", ["AFFIRMED 09/21/2023", "Final Opinion and Order", "too short"])
def test_gate_rejects_short_quotes_even_if_they_are_on_the_page(quote):
    page = PAGE + quote + "\n"
    (g,) = extract.gate_quotes([extract.RawReason(quote=quote, source="LUBA")], page)
    assert g.status == "rejected"
    assert g.reason == "too_short"


def test_gate_rejects_quotes_that_are_mostly_capitals():
    q = "FINAL OPINION AND ORDER OF THE LAND USE BOARD OF APPEALS ENTERED TODAY"
    (g,) = extract.gate_quotes([extract.RawReason(quote=q, source="LUBA")], PAGE + q)
    assert g.status == "rejected"
    assert g.reason == "all_caps"


def test_gate_rejects_overlong_quotes():
    q = " ".join(["word"] * 60)
    (g,) = extract.gate_quotes([extract.RawReason(quote=q, source="county")], q)
    assert g.status == "rejected"
    assert g.reason == "too_long"


def test_gate_drops_duplicate_quotes_keeping_the_first():
    r = extract.RawReason(quote=GOOD, source="county")
    out = extract.gate_quotes([r, r], PAGE)
    assert [g.status for g in out] == ["accepted", "rejected"]
    assert out[1].reason == "duplicate"


# ---- local-only guard --------------------------------------------------------------------

LOCAL = ModelInfo(name="qwen3:30b-instruct", digest="sha256:abc", remote=False)
CLOUD_TAG = ModelInfo(name="qwen3-coder:480b-cloud", digest="", remote=True)


def test_a_local_model_is_allowed():
    extract.check_model("qwen3:30b-instruct", [LOCAL], allow_cloud=False, confirm=None)


def test_an_unknown_model_is_refused():
    with pytest.raises(LocalOnlyError, match="not installed"):
        extract.check_model("nope:1b", [LOCAL], allow_cloud=False, confirm=None)


def test_cloud_tags_are_detected_by_name_and_by_flag():
    assert extract.is_cloud(CLOUD_TAG)
    assert extract.is_cloud(ModelInfo(name="x:cloud", digest="", remote=False))
    assert extract.is_cloud(ModelInfo(name="x-cloud", digest="", remote=False))
    assert extract.is_cloud(ModelInfo(name="x:1b", digest="", remote=True))
    assert not extract.is_cloud(LOCAL)


def test_cloud_model_is_refused_without_confirmation():
    with pytest.raises(CloudModelRefused):
        extract.check_model(CLOUD_TAG.name, [CLOUD_TAG], allow_cloud=False, confirm=None)


def test_cloud_model_needs_the_exact_typed_phrase():
    with pytest.raises(CloudModelRefused):
        extract.check_model(
            CLOUD_TAG.name, [CLOUD_TAG], allow_cloud=False, confirm=lambda warning: "yes"
        )
    extract.check_model(
        CLOUD_TAG.name,
        [CLOUD_TAG],
        allow_cloud=False,
        confirm=lambda warning: extract.CLOUD_PHRASE,
    )


def test_cloud_warning_mentions_personal_information():
    seen = []
    extract.check_model(
        CLOUD_TAG.name,
        [CLOUD_TAG],
        allow_cloud=False,
        confirm=lambda w: seen.append(w) or extract.CLOUD_PHRASE,
    )
    assert "personal" in seen[0].lower()
    assert extract.CLOUD_PHRASE in seen[0]


def test_allow_cloud_flag_skips_the_prompt():
    extract.check_model(CLOUD_TAG.name, [CLOUD_TAG], allow_cloud=True, confirm=None)


@pytest.mark.parametrize(
    "host", ["http://localhost:11434", "http://127.0.0.1:11434", "http://[::1]:11434"]
)
def test_local_hosts_are_accepted(host):
    extract.check_host(host)


@pytest.mark.parametrize(
    "host", ["http://example.com:11434", "https://ollama.com", "http://10.0.0.5"]
)
def test_remote_hosts_are_refused(host):
    with pytest.raises(LocalOnlyError):
        extract.check_host(host)


# ---- request -----------------------------------------------------------------------------


def test_request_is_deterministic_json_with_fixed_settings():
    req = extract.build_request("qwen3:30b-instruct", "PROMPT", temperature=0, seed=42)
    assert req["model"] == "qwen3:30b-instruct"
    assert req["prompt"] == "PROMPT"
    assert req["stream"] is False
    assert req["format"] == "json"
    assert req["options"] == {"temperature": 0, "seed": 42}


# ---- running a document ------------------------------------------------------------------


class FakeModel:
    """A stand-in for the model: returns canned replies by page text."""

    def __init__(self, replies):
        self.replies = replies
        self.calls = []

    def __call__(self, request):
        self.calls.append(request)
        for key, reply in self.replies.items():
            if key in request["prompt"]:
                return {"response": reply, "eval_count": 7}
        return {"response": _reply([]), "eval_count": 1}


def _run(pages, model, tmp_path=None, **kw):
    return extract.run_document(
        doc_id="doc1",
        pdf_sha256=SHA,
        pages=pages,
        prompt_text="P\nPAGE TEXT:\n",
        model=LOCAL,
        send=model,
        **kw,
    )


def test_run_document_returns_one_result_per_page_in_order():
    model = FakeModel({"removing farmland": _reply([{"quote": GOOD, "source": "county"}])})
    res = _run(["Caption page", PAGE], model)
    assert [p.page for p in res.pages] == [1, 2]
    assert res.pages[0].accepted == []
    assert [g.quote for g in res.pages[1].accepted] == [GOOD]


def test_run_document_skips_blank_pages_without_calling_the_model():
    model = FakeModel({})
    res = _run(["   \n", "Some text here"], model)
    assert len(model.calls) == 1
    assert res.pages[0].skipped == "blank"


def test_fabricated_quotes_never_reach_accepted():
    bad = _reply(
        [{"quote": "The project complies with all applicable regulations.", "source": "county"}]
    )
    res = _run(["Caption page"], FakeModel({"Caption": bad}))
    p = res.pages[0]
    assert p.accepted == []
    assert [g.reason for g in p.rejected] == ["not_on_page"]


def test_malformed_model_output_is_recorded_not_raised():
    res = _run(["Caption page"], FakeModel({"Caption": "garbage"}))
    assert res.pages[0].error
    assert res.pages[0].accepted == []


def test_reasons_are_sorted_by_page_then_position_before_ids_are_assigned():
    r1 = {"quote": GOOD, "source": "county"}
    model = FakeModel({"removing farmland": _reply([r1])})
    res = _run([PAGE, PAGE.replace("12", "22")], model)
    ids = [r.id for r in res.reasons()]
    assert ids == ["doc1-p1-r1", "doc1-p2-r1"]


def test_ids_are_stable_across_runs():
    model = FakeModel({"removing farmland": _reply([{"quote": GOOD, "source": "county"}])})
    a = [r.id for r in _run([PAGE], model).reasons()]
    b = [r.id for r in _run([PAGE], model).reasons()]
    assert a == b


# ---- manifest ----------------------------------------------------------------------------


def test_manifest_records_everything_needed_to_repeat_the_run():
    model = FakeModel({"removing farmland": _reply([{"quote": GOOD, "source": "county"}])})
    res = _run([PAGE], model, temperature=0, seed=42)
    m = extract.build_manifest(
        res,
        pipeline_commit="abc123",
        prompt_sha256="c" * 64,
        model=LOCAL,
        temperature=0,
        seed=42,
        host="http://localhost:11434",
        cloud=False,
        run_at="2026-10-20T12:00:00+00:00",
    )
    assert m["pipeline_commit"] == "abc123"
    assert m["prompt_sha256"] == "c" * 64
    assert m["model"] == {"name": LOCAL.name, "digest": LOCAL.digest}
    assert m["settings"] == {"temperature": 0, "seed": 42}
    assert m["input"] == {"document_id": "doc1", "pdf_sha256": SHA, "page_count": 1}
    assert m["cloud"] is False
    assert m["counts"] == {"accepted": 1, "review": 0, "rejected": 0, "page_errors": 0}
    assert len(m["output_sha256"]) == 64


def test_manifest_output_hash_changes_when_output_changes():
    kw = dict(
        pipeline_commit="x",
        prompt_sha256="c" * 64,
        model=LOCAL,
        temperature=0,
        seed=42,
        host="h",
        cloud=False,
        run_at="t",
    )
    a = _run(
        [PAGE], FakeModel({"removing farmland": _reply([{"quote": GOOD, "source": "county"}])})
    )
    b = _run([PAGE], FakeModel({}))
    assert (
        extract.build_manifest(a, **kw)["output_sha256"]
        != extract.build_manifest(b, **kw)["output_sha256"]
    )


def test_output_document_has_the_accepted_reasons_but_marks_them_machine_extracted():
    model = FakeModel({"removing farmland": _reply([{"quote": GOOD, "source": "county"}])})
    out = extract.output_document(_run([PAGE], model))
    (r,) = out["reasons"]
    assert r["quote"] == GOOD
    assert r["pdf_page"] == 1
    assert r["document_id"] == "doc1"
    assert r["hand_checked"] is False
    assert r["category"] == "other_uncoded"
    assert r["machine_source"] == "county"


# ---- local server calls (a throwaway server on this computer) ----------------------------


def _serve(handler_cls):
    import threading
    from http.server import HTTPServer

    srv = HTTPServer(("127.0.0.1", 0), handler_cls)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def test_list_models_and_send_talk_to_the_local_server():
    from http.server import BaseHTTPRequestHandler

    seen = {}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, obj):
            body = json.dumps(obj).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            self._json(
                {
                    "models": [
                        {"name": "qwen3:30b-instruct", "digest": "d1"},
                        {"name": "big:cloud", "digest": "", "remote_host": "https://ollama.com"},
                    ]
                }
            )

        def do_POST(self):
            seen["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self._json({"response": '{"has_reasons": false, "reasons": []}', "eval_count": 3})

    srv, host = _serve(H)
    try:
        models = extract.list_models(host)
        assert [m.name for m in models] == ["qwen3:30b-instruct", "big:cloud"]
        assert models[0].digest == "d1" and not models[0].remote
        assert models[1].remote
        req = extract.build_request("qwen3:30b-instruct", "hi", temperature=0, seed=1)
        reply = extract.make_sender(host)(req)
        assert reply["eval_count"] == 3
        assert seen["body"]["options"] == {"temperature": 0, "seed": 1}
    finally:
        srv.shutdown()


def test_senders_refuse_remote_hosts_before_connecting():
    with pytest.raises(LocalOnlyError):
        extract.list_models("http://example.com:11434")
    with pytest.raises(LocalOnlyError):
        extract.make_sender("http://example.com:11434")


# ---- command line ------------------------------------------------------------------------


@pytest.fixture
def cli_env(tmp_path, monkeypatch):
    """Fakes the PDF text and the model server so the command runs without either."""
    from oregon_farmland_solar import cli

    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF fake")
    monkeypatch.setattr(extract, "list_models", lambda host: [LOCAL, CLOUD_TAG])
    reply = _reply([{"quote": GOOD, "source": "county"}])
    monkeypatch.setattr(
        extract,
        "make_sender",
        lambda host: lambda req: {"response": reply if "farmland" in req["prompt"] else _reply([])},
    )
    monkeypatch.setattr(cli, "extract_pages", lambda p: ["Caption", PAGE])
    monkeypatch.setattr(cli, "_git_commit", lambda: "abc123")
    out = tmp_path / "out"
    base = ["extract", str(pdf), "--doc-id", "doc1", "--out-dir", str(out)]
    return base, out, pdf


def test_cli_extract_writes_candidates_and_manifest(cli_env):
    from oregon_farmland_solar.cli import main

    base, out, pdf = cli_env
    assert main(base) == 0
    cands = json.loads((out / "doc1.candidates.json").read_text())
    assert [r["id"] for r in cands["reasons"]] == ["doc1-p2-r1"]
    man = json.loads((out / "doc1.manifest.json").read_text())
    assert man["input"]["pdf_sha256"] == hashlib.sha256(pdf.read_bytes()).hexdigest()
    assert man["pipeline_commit"] == "abc123"
    assert man["model"]["name"] == "qwen3:30b-instruct"
    assert man["settings"] == {"temperature": 0, "seed": 42}
    assert man["cloud"] is False
    assert len(man["prompt_sha256"]) == 64


def test_cli_extract_can_limit_to_some_pages(cli_env):
    from oregon_farmland_solar.cli import main

    base, out, _ = cli_env
    assert main([*base, "--pages", "1"]) == 0
    cands = json.loads((out / "doc1.candidates.json").read_text())
    assert cands["reasons"] == []


def test_cli_extract_refuses_a_cloud_model_when_it_cannot_ask(cli_env, monkeypatch):
    import sys

    from oregon_farmland_solar.cli import main

    base, out, _ = cli_env
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
    assert main([*base, "--model", CLOUD_TAG.name]) == 1
    assert not (out / "doc1.candidates.json").exists()


def test_cli_extract_allows_a_cloud_model_with_the_explicit_flag(cli_env):
    from oregon_farmland_solar.cli import main

    base, out, _ = cli_env
    assert main([*base, "--model", CLOUD_TAG.name, "--allow-cloud"]) == 0
    assert json.loads((out / "doc1.manifest.json").read_text())["cloud"] is True


def test_cli_extract_refuses_a_remote_host(cli_env):
    from oregon_farmland_solar.cli import main

    base, out, _ = cli_env
    assert main([*base, "--host", "http://example.com:11434"]) == 1
