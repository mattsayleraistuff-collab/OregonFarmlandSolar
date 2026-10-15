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

## Project layout
- `src/oregon_farmland_solar/` – application code
- `tests/` – tests (write the test first)
- `data/raw/` – downloaded source data (git-ignored; see `docs/data-sources.md` to re-obtain)
- `data/processed/` – derived datasets
- `docs/methodology.md` – audit log of analyses and data manipulations
- `docs/data-sources.md` – where every dataset came from

## Security notes
This repository is public. Never commit API keys, tokens, or credentials. Keep them in a local `.env` file (git-ignored) and read them from environment variables.

## Known limitations
- Scaffold only; nothing is implemented yet.
- _TODO: add data coverage, geographic, and permit-record limitations as they are discovered._
