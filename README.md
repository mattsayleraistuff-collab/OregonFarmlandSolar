# OregonFarmlandSolar

## What it does
A 2-week sprint project to build a working map and dashboard that tracks the reasons solar-on-farm permits are approved or denied in Oregon.

Status: scaffold only. No data, analysis, or app code yet.

## How to use
_TODO: fill in once the app exists (how to load data, run the dashboard, read the map)._

## Installation
Requires [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/mattsayleraistuff-collab/OregonFarmlandSolar.git
cd OregonFarmlandSolar
uv sync
```

Run checks:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

CI (GitHub Actions) runs the same three checks on every push to `main` and on pull requests.

## Data model
`project -> proceeding -> document -> reason`. Local proceedings record what a county decided; appeal proceedings record what a reviewing body (for example LUBA) did. Each coded reason has a category from `data/taxonomy/reasons.yaml`, a verbatim quote, and a PDF page number. See `docs/methodology.md` for the rules and the decision log.

Source PDFs are kept locally and are not published. The repo holds structured data, quotes with page references, and a manifest of document checksums.

## Project layout
- `src/oregon_farmland_solar/` – application code
- `tests/` – tests (write the test first)
- `data/taxonomy/` – reason taxonomy (versioned YAML)
- `data/records/` – structured records (JSON)
- `data/raw/` – source PDFs and other originals (git-ignored, kept locally; see `docs/data-sources.md`)
- `data/processed/` – derived datasets
- `docs/methodology.md` – decision record: why analyses and data choices were made
- `docs/data-sources.md` – where every dataset came from

## Security notes
This repository is public. Never commit API keys, tokens, or credentials. Keep them in a local `.env` file (git-ignored) and read them from environment variables.

## Known limitations
- Schema, taxonomy and validators exist; no real decisions have been coded yet.
- The reason taxonomy is a draft based on three sample projects.
- Quote verification and personal-information checks run locally against the source PDFs, which are not published.
- _TODO: add data coverage, geographic, and permit-record limitations as they are discovered._
