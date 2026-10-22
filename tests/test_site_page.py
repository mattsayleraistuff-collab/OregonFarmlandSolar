"""Checks on the site's page and scripts: structure, safety rules, and the pure-helper tests."""

import re
import shutil
import subprocess

import pytest

from conftest import REPO_ROOT

SITE = REPO_ROOT / "site"
INDEX = (SITE / "index.html").read_text(encoding="utf-8")
APP = (SITE / "js" / "app.js").read_text(encoding="utf-8")


def test_node_helper_tests_pass():
    """Runs tests/js (pure helpers: map projection, buckets, keyboard moves, data states)."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    files = sorted(str(p) for p in (REPO_ROOT / "tests" / "js").glob("*.test.mjs"))
    done = subprocess.run([node, "--test", *files], capture_output=True, text=True, cwd=REPO_ROOT)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-1000:]


def test_the_six_regions_exist_and_are_in_the_nav():
    for region in ("overview", "map", "reasons", "appeal-examples", "appeals", "method"):
        assert f'<section class="ofs-region" id="{region}"' in INDEX
        assert f'href="#{region}"' in INDEX


def test_the_body_uses_the_design_class_and_a_skip_link():
    assert '<body class="ofs-page">' in INDEX
    assert 'class="ofs-skip" href="#main"' in INDEX
    assert '<main id="main">' in INDEX


def test_the_page_uses_only_the_design_stylesheets():
    assert 'href="css/site-tokens.css"' in INDEX
    assert 'href="css/site.css"' in INDEX
    assert not (SITE / "style.css").exists()


def test_required_labels_are_present():
    text = INDEX + APP
    for label in (
        "County outcome",
        "Appeal outcome (where in our records)",
        "Real records",
        "Synthetic demo data",
        "hand-checked",
        "machine-extracted",
        "Only ",
    ):
        assert label in text, label


def test_the_word_final_only_appears_in_the_not_final_notice():
    text = re.sub(r"<script.*?</script>", "", INDEX, flags=re.S)
    for m in re.finditer(r"final", text + APP, flags=re.I):
        around = (text + APP)[max(0, m.start() - 40) : m.end() + 20].lower()
        assert (
            "not &ldquo;final" in around
            or "not \\u201cfinal" in around
            or "findings" in around
            # LUBA's own deadline wording; it is not how we label an outcome.
            or "decision becomes final" in around
        ), around


def _code(text: str) -> str:
    """Script text without // comments, so a comment can mention a banned call."""
    return re.sub(r"(?m)^\s*//.*$", "", text)


def test_data_is_never_put_in_the_page_with_innerhtml():
    code = _code(APP)
    for banned in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval("):
        assert banned not in code, banned


def test_scripts_use_relative_urls_only():
    for p in (SITE / "js").glob("*.js"):
        text = p.read_text(encoding="utf-8")
        assert not re.search(r"""(fetch|import)\(?\s*["'`]/[^/]""", text), p.name
        urls = re.findall(r"https?://[^\s\"'`]+", _code(text))
        assert urls in ([], ["http://www.w3.org/2000/svg"]), (p.name, urls)  # an XML namespace


def test_every_import_resolves_to_a_file_that_ships():
    for m in re.finditer(r'from "\./([\w.-]+)"', APP):
        assert (SITE / "js" / m.group(1)).exists(), m.group(1)


def test_quotes_are_shown_by_the_config_flag():
    config = (SITE / "js" / "config.js").read_text(encoding="utf-8")
    assert "export const SHOW_QUOTES = true;" in config
    assert "SHOW_QUOTES" in APP


def test_the_explainer_records_what_it_was_checked_against():
    assert "VERIFY BEFORE LAUNCH" not in INDEX
    assert "OAR 661-010-0071" in INDEX
    assert "frequently-asked-questions" in INDEX
    for term in ("affirm", "reverse", "remand", "dismiss", "petitioner", "respondent"):
        assert term in INDEX.lower(), term


def test_the_pages_workflow_installs_node_before_the_tests():
    for name in ("ci.yml", "pages.yml"):
        text = (REPO_ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
        assert "actions/setup-node@v4" in text


def test_bold_terms_inside_a_step_do_not_start_a_new_line():
    css = (SITE / "css" / "site.css").read_text(encoding="utf-8")
    assert not re.search(r"\.ofs-steps b\s*[,{]", css), "style only the step title, not every <b>"
    assert re.search(r"\.ofs-steps li > div > b\s*\{[^}]*display:\s*block", css)


def test_choosing_a_county_from_the_table_brings_its_card_into_view():
    table_click = APP[APP.index("table.addEventListener") :]
    table_click = table_click[: table_click.index("});")]
    assert "reveal: true" in table_click
    select_county = APP[APP.index("function selectCounty") : APP.index("function onMapKey")]
    assert "reveal" in select_county
    assert "scrollIntoView" in select_county
    assert 'tabindex: "-1"' in APP[APP.index("function renderCountyDetail") :]
    assert "preventScroll" in select_county
