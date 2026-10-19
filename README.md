# OregonFarmlandSolar

## What it does
A 2-week sprint project to build a working map and dashboard that tracks the reasons solar-on-farm permits are approved or denied in Oregon.

Status: scaffold only. No data, analysis, or app code yet.

## Scope and coverage
This tracks the reasons given in the decisions we have, not every solar-on-farmland permit in Oregon.

- **Records:** county decisions obtained through a public records request, plus three hand-collected LUBA appeals (sample cases).
- **Outcomes:** the *county outcome* is the headline result. An *appeal outcome (where in our records)* is shown only where we hold a LUBA or court document. We do not claim a "final" outcome: a county decision may have been appealed, remanded or reversed without a record of that here.
- **LUBA samples:** appealed cases skew toward contested projects, and three cases are far too few for rates. They are reported separately as case studies, with no percentages, and never pooled with county decisions.
- **Not covered:** appeals and court decisions we did not collect, projects decided outside the records request, and anything after the records were gathered.

Any dashboard or map built from this data must show this scope statement.

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

Validate a records file (add `--pdf-dir <folder>` to also check quotes against local PDFs; needs poppler's `pdftotext`):

```bash
uv run ofs validate data/records/marion-silver-creek-solar.json
```

CI (GitHub Actions) runs the same three checks on every push to `main` and on pull requests.

## Data model
`project -> proceeding -> document -> reason`. Local proceedings record what a county decided; appeal proceedings record what a reviewing body (for example LUBA) did. Each coded reason has a category from `data/taxonomy/reasons.yaml`, a verbatim quote, and a PDF page number. See `docs/methodology.md` for the rules and the decision log.

Source PDFs are kept locally and are not published. The repo holds structured data, quotes with page references, and a manifest of document checksums.

## Project layout
- `src/oregon_farmland_solar/` – application code (Google-style docstrings, enforced by ruff)
- `tests/` – tests (write the test first)
- `data/taxonomy/` – reason taxonomy (versioned YAML)
- `data/records/` – structured records (JSON)
- `data/raw/` – source PDFs and other originals (git-ignored, kept locally; see `docs/data-sources.md`)
- `data/processed/` – derived datasets
- `docs/methodology.md` – decision record: why analyses and data choices were made
- `docs/data-sources.md` – where every dataset came from

## Security notes
This repository is public. Never commit API keys, tokens, or credentials. Keep them in a local `.env` file (git-ignored) and read them from environment variables.

Branch protection for `main` (pull request required, `test` check must pass, no force pushes or deletion) is documented in `.github/rulesets/protect-main.json`. GitHub does not read this file automatically; it is a copy of the ruleset imported in the repository settings, so update both together.

## Known limitations
- Schema, taxonomy and validators exist; two sample projects (Marion, Yamhill) are coded; Marion is hand-checked, Yamhill awaits review.
- The reason taxonomy is a draft based on three sample projects.
- Quote verification and personal-information checks run locally against the source PDFs, which are not published.
- Coverage is limited to the records obtained (see Scope and coverage); appeal and court outcomes are incomplete.
- _TODO: add geographic and permit-record limitations as they are discovered._
