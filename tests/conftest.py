from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TAXONOMY_PATH = REPO_ROOT / "data" / "taxonomy" / "reasons.yaml"


@pytest.fixture
def taxonomy_path() -> Path:
    return TAXONOMY_PATH


@pytest.fixture
def raw_dataset() -> dict:
    """A small, valid, entirely synthetic dataset (plain dicts, as loaded from JSON)."""
    return {
        "projects": [
            {
                "id": "p1",
                "name": "Synthetic Solar A",
                "county": "Testco",
                "source_type": "luba",
                "synthetic": True,
            }
        ],
        "proceedings": [
            {
                "id": "pr-local",
                "project_id": "p1",
                "level": "local",
                "body": "Board of Commissioners",
                "local_outcome": "denied",
                "synthetic": True,
            },
            {
                "id": "pr-appeal",
                "project_id": "p1",
                "level": "appeal",
                "body": "LUBA",
                "appeal_outcome": "affirmed",
                "synthetic": True,
            },
        ],
        "documents": [
            {
                "id": "d-order",
                "proceeding_id": "pr-local",
                "document_type": "county_decision",
                "synthetic": True,
            },
            {
                "id": "d-luba",
                "proceeding_id": "pr-appeal",
                "document_type": "appellate_opinion",
                "synthetic": True,
            },
        ],
        "reasons": [
            {
                "id": "r1",
                "proceeding_id": "pr-local",
                "document_id": "d-order",
                "category": "neighbor_farm_impacts",
                "quote": "The facility would harm adjacent vineyard operations.",
                "pdf_page": 3,
                "synthetic": True,
            }
        ],
    }
