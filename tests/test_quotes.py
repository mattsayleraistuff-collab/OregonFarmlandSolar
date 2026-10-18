from oregon_farmland_solar.quotes import check_quote

PAGE = """
 4   Petitioner filed applications with the county for conditional use permit
 5   and site design approval for a 12-acre solar facility on the eastern half of the
 6   property, surrounded by a perimeter fence.  The facility consists of solar pan-
 7   els in aluminum frames, mounted on racks.
"""


def test_exact_quote_found():
    r = check_quote("conditional use permit and site design approval", PAGE)
    assert r.found and r.exact


def test_line_numbers_whitespace_and_hyphenation_are_ignored():
    r = check_quote("solar panels in aluminum frames, mounted on racks", PAGE)
    assert r.found and r.exact


def test_curly_quotes_and_case_are_ignored():
    page = "The board said it was “not compatible” with farm use."
    assert check_quote('It was "NOT COMPATIBLE" with farm use', page).found


def test_ocr_noise_tolerated_by_fuzzy_match():
    page = "BEFORE Tiffi LAND USE BOARD OF APPEALS OFTHESTATEOFOREGON Petitioner appeals"
    r = check_quote("Before the Land Use Board of Appeals of the State of Oregon", page)
    assert r.found


def test_fabricated_quote_not_found():
    r = check_quote("The county found the facility would devastate the local tourism economy", PAGE)
    assert not r.found


def test_short_quote_requires_exact_match():
    assert not check_quote("solar farm", PAGE).found


def test_empty_inputs_not_found():
    assert not check_quote("", PAGE).found
    assert not check_quote("something", "").found
