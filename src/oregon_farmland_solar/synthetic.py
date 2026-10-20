"""Seeded generator for synthetic demo records shaped like the expected county approvals.

Everything produced here is invented. It exists so the map and dashboard can be built and
demonstrated before the real records arrive. The shape mirrors what the records request is
expected to return: county decisions that approved a project, one document per decision, no
appeals. Distributions (counties, acreage, outcomes, reasons) are arbitrary choices and say
nothing about real Oregon decisions.

Every record carries ``synthetic: true`` and every quote starts with ``[SYNTHETIC]``, so a
synthetic record cannot be mistaken for a real one, and ``check_dataset`` refuses to mix the
two in a single chain of records.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any

# Defaults used for the committed demo file; the same seed always gives the same records.
DEFAULT_SEED = 20261022
DEFAULT_COUNT = 60

OREGON_COUNTIES = (
    "Baker",
    "Benton",
    "Clackamas",
    "Clatsop",
    "Columbia",
    "Coos",
    "Crook",
    "Curry",
    "Deschutes",
    "Douglas",
    "Gilliam",
    "Grant",
    "Harney",
    "Hood River",
    "Jackson",
    "Jefferson",
    "Josephine",
    "Klamath",
    "Lake",
    "Lane",
    "Lincoln",
    "Linn",
    "Malheur",
    "Marion",
    "Morrow",
    "Multnomah",
    "Polk",
    "Sherman",
    "Tillamook",
    "Umatilla",
    "Union",
    "Wallowa",
    "Wasco",
    "Washington",
    "Wheeler",
    "Yamhill",
)

_LAND_CLASSES = (
    "EFU",
    "EFU, high-value farmland",
    "EFU, non-high-value farmland",
)

_OUTCOMES = ("approved", "approved_with_conditions")

# Reason categories used for approvals, with invented quotes that read as approval findings.
_APPROVAL_QUOTES: dict[str, tuple[str, ...]] = {
    "state_farmland_standards": (
        "The proposal satisfies the state farmland-use standards for a photovoltaic facility.",
        "The facility meets the siting standards for solar on agricultural land.",
    ),
    "goal_exception_criteria": (
        "The applicant has met the criteria for the requested exception.",
        "The exception criteria are satisfied for the proposed site.",
    ),
    "neighbor_farm_impacts": (
        "The facility will not significantly change farm practices on surrounding lands.",
        "No significant increase in the cost of nearby farm practices was shown.",
    ),
    "visual_tourism_impacts": (
        "The facility is screened and will not significantly affect scenic or tourism values.",
        "Visual effects are limited by the proposed setbacks and landscaping.",
    ),
    "farmland_loss": (
        "The site has limited agricultural productivity and little high-value soil is affected.",
        "The impact on productive farmland is small and the land can return to farm use.",
    ),
}
_APPROVAL_CATEGORIES = tuple(_APPROVAL_QUOTES)

_NOTE = "Synthetic: invented to test the layout. Not a real finding."


def generate(seed: int, count: int) -> dict[str, Any]:
    """Generates a synthetic dataset of county approvals.

    Each project has one local proceeding (approved or approved with conditions), one county
    decision document and one to three reasons. The result is plain JSON-compatible data in
    the same shape as a records file.

    Args:
        seed: Seed for the random generator; the same seed and count always give the same data.
        count: Number of projects to generate.

    Returns:
        A dict with ``projects``, ``proceedings``, ``documents`` and ``reasons`` lists.

    Raises:
        ValueError: If ``count`` is less than 1.
    """
    if count < 1:
        raise ValueError("count must be at least 1")
    rng = random.Random(seed)
    out: dict[str, list[dict[str, Any]]] = {
        "projects": [],
        "proceedings": [],
        "documents": [],
        "reasons": [],
    }
    for n in range(1, count + 1):
        key = f"syn-{n:03d}"
        county = rng.choice(OREGON_COUNTIES)
        pages = rng.randint(6, 40)
        out["projects"].append(
            {
                "id": key,
                "synthetic": True,
                "name": f"Synthetic Solar {n:03d}",
                "county": county,
                "source_type": "county",
                "acres": round(rng.uniform(5, 200), 1),
                "land_class_as_stated": rng.choice(_LAND_CLASSES),
                "dual_use": rng.choice((True, False, None)),
            }
        )
        out["proceedings"].append(
            {
                "id": f"{key}-local",
                "synthetic": True,
                "project_id": key,
                "level": "local",
                "body": f"{county} County Board of Commissioners",
                "decision_date": _random_date(rng),
                "local_outcome": rng.choice(_OUTCOMES),
            }
        )
        out["documents"].append(
            {
                "id": f"{key}-doc",
                "synthetic": True,
                "proceeding_id": f"{key}-local",
                "document_type": "county_decision",
                "page_count": pages,
            }
        )
        for i, category in enumerate(
            rng.sample(_APPROVAL_CATEGORIES, k=rng.randint(1, 3)), start=1
        ):
            out["reasons"].append(
                {
                    "id": f"{key}-r{i}",
                    "synthetic": True,
                    "proceeding_id": f"{key}-local",
                    "document_id": f"{key}-doc",
                    "category": category,
                    "quote": f"[SYNTHETIC] {rng.choice(_APPROVAL_QUOTES[category])}",
                    "pdf_page": rng.randint(1, pages),
                    "note": _NOTE,
                    "hand_checked": False,
                }
            )
    return out


def _random_date(rng: random.Random) -> str:
    """Picks an ISO date between 2012-01-01 and 2025-12-31."""
    start = date(2012, 1, 1)
    span = (date(2025, 12, 31) - start).days
    return (start + timedelta(days=rng.randint(0, span))).isoformat()
