"""Checks the design tokens: the CSS the site uses matches the handoff files, and the colour
pairings the design relies on meet WCAG 2.2 AA when computed here (not taken from the doc)."""

import json
import re

import pytest

from conftest import REPO_ROOT

TOKENS_CSS = REPO_ROOT / "site" / "css" / "site-tokens.css"
SITE_CSS = REPO_ROOT / "site" / "css" / "site.css"
DESIGN = REPO_ROOT / "design"

# (foreground, background, minimum ratio). Text needs 4.5, graphics and control edges 3.
PAIRS = [
    ("ink", "bg", 4.5), ("ink", "surface", 4.5), ("ink", "sunken", 4.5),
    ("ink-muted", "bg", 4.5), ("ink-muted", "surface", 4.5), ("ink-muted", "sunken", 4.5),
    ("accent", "bg", 4.5), ("accent", "surface", 4.5), ("accent", "sunken", 4.5),
    ("on-accent", "accent", 4.5),
    ("ink", "info-bg", 4.5), ("ink", "caution-bg", 4.5),
    ("synth-ink", "synth-bg", 4.5),
    ("approve-ink", "approve-bg", 4.5), ("deny-ink", "deny-bg", 4.5),
    ("seq-1-ink", "seq-1", 4.5), ("seq-2-ink", "seq-2", 4.5), ("seq-3-ink", "seq-3", 4.5),
    ("seq-4-ink", "seq-4", 4.5), ("seq-5-ink", "seq-5", 4.5),
    ("border-strong", "bg", 3), ("border-strong", "surface", 3), ("border-strong", "sunken", 3),
    ("focus", "bg", 3), ("focus", "surface", 3), ("focus", "sunken", 3),
    ("map-stroke", "bg", 3), ("map-stroke", "surface", 3),
    ("info-border", "bg", 3), ("caution-border", "bg", 3),
    ("approve-border", "approve-bg", 3), ("approve-border", "bg", 3),
    ("deny-border", "deny-bg", 3), ("deny-border", "bg", 3),
]  # fmt: skip


def _vars(block: str) -> dict[str, str]:
    return dict(re.findall(r"--([a-z0-9-]+):\s*(#[0-9A-Fa-f]{6})\s*;", block))


def _themes() -> dict[str, dict[str, str]]:
    css = TOKENS_CSS.read_text(encoding="utf-8")
    light = _vars(css.split("@media", 1)[0])
    dark_block = css.split("@media (prefers-color-scheme: dark)", 1)[1].split("}\n}", 1)[0]
    dark = {**light, **_vars(dark_block)}
    return {"light": light, "dark": dark}


def _luminance(hex_colour: str) -> float:
    def channel(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = (int(hex_colour[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def ratio(a: str, b: str) -> float:
    """WCAG 2 contrast ratio between two #RRGGBB colours."""
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_ratio_matches_known_values():
    assert ratio("#000000", "#FFFFFF") == pytest.approx(21.0)
    assert ratio("#777777", "#FFFFFF") == pytest.approx(4.48, abs=0.01)


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize(("fg", "bg", "minimum"), PAIRS)
def test_pairing_meets_wcag_aa(theme, fg, bg, minimum):
    colours = _themes()[theme]
    got = ratio(colours[fg], colours[bg])
    assert got >= minimum, f"{theme}: {fg} on {bg} is {got:.2f}:1, needs {minimum}:1"


def test_the_sequential_ramp_gets_brighter_against_the_page_as_counts_rise():
    """More cases must stand out more from the page in both themes."""
    for theme, colours in _themes().items():
        r = [ratio(colours[f"seq-{n}"], colours["bg"]) for n in range(1, 6)]
        assert r == sorted(r), f"{theme}: ramp contrast {r}"


def test_site_tokens_match_the_copy_in_the_design_folder():
    for name in ("site-tokens.css", "site.css"):
        assert (REPO_ROOT / "site" / "css" / name).read_bytes() == (
            DESIGN / "assets" / name
        ).read_bytes()


def test_dtcg_tokens_agree_with_the_css_light_values():
    data = json.loads((DESIGN / "assets" / "tokens.dtcg.json").read_text(encoding="utf-8"))
    light = _themes()["light"]
    found = {}

    def walk(node):
        if isinstance(node, dict):
            if (
                "$value" in node
                and isinstance(node["$value"], str)
                and node["$value"].startswith("#")
            ):
                found[len(found)] = node["$value"].upper()
            for v in node.values():
                walk(v)

    walk(data)
    css_values = {v.upper() for v in light.values()}
    assert found, "no colour tokens found in the DTCG file"
    assert set(found.values()) <= css_values


def test_stylesheets_load_nothing_from_other_servers():
    for path in (TOKENS_CSS, SITE_CSS):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"https?://|@import|url\(\s*['\"]?//", text), path.name
