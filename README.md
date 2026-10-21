# OregonFarmlandSolar

## What it does
A 2-week sprint project to build a working map and dashboard that tracks the reasons solar-on-farm permits are approved or denied in Oregon.

Status: scaffold only. No data, analysis, or app code yet.

## Scope and coverage
This tracks the reasons given in the decisions we have, not every solar-on-farmland permit in Oregon.

- **Records:** county decisions from a public records request, plus three hand-collected LUBA appeals (sample cases). The agency confirmed the county records include **approved decisions only**: no denied or withdrawn applications. County records do not carry local decision numbers.
- **Outcomes:** the *county outcome* is the headline result (approved, for every county record). An *appeal outcome (where in our records)* is shown only where we hold a LUBA or court document. We do not claim a "final" outcome: a county decision may have been appealed, remanded or reversed without a record of that here.
- **Denials:** the only county denials in the data are two of the three LUBA sample cases (Marion and Yamhill); the third (Jackson) is a county approval that LUBA reversed. The county records cannot show how often projects are denied, why denials differ from approvals, or approval rates of any kind.
- **LUBA samples:** appealed cases skew toward contested projects, and three cases are far too few for rates. They are reported separately as case studies, with no percentages, and never pooled with county decisions.
- **Not covered:** appeals and court decisions we did not collect, projects decided outside the records request, and anything after the records were gathered.

Any dashboard or map built from this data must show this scope statement.

## How to use
The site is a static page (currently a placeholder awaiting the design). To preview it locally:

```
uv run ofs stage-site
python3 -m http.server --directory _site 8000   # then open http://localhost:8000
```

Pushes to `main` deploy it to GitHub Pages through `.github/workflows/pages.yml` (Pages must be set to deploy from GitHub Actions in the repository settings).

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

Write the synthetic demo records (seeded; the same seed always gives the same file):

```bash
uv run ofs synth --seed 20261022 --count 60
```

The committed demo file is `data/synthetic/synthetic-county-approvals.json`. Every record in it is invented and flagged `synthetic: true`, and every quote starts with `[SYNTHETIC]`. It stands in for the county approvals expected from the records request until the real records arrive. Any map or chart that uses it must label it as synthetic.

Build the JSON the website reads (per-county counts, category counts and case files, from the committed records):

```bash
uv run ofs site-data
```

The output, `site/data/site-data.json`, keeps real and synthetic records in separate sections and never pools results across source types. The build stops if the records fail the checks, if real and synthetic records are mixed, or if a quote looks like personal information. The committed file must match what the command produces from the committed records (a test checks this), so re-run it whenever records change.

### Rebuilding the county layer (optional)
You do not need this to run the checks or view the site: the web-sized county layer, `data/geo/oregon-counties.geojson` (about 240 KB), and its provenance file are committed. Rebuild it only to refresh it from the source.

- **Needs:** network access, and [Node.js](https://nodejs.org/) for the simplification step (it runs mapshaper through `npx`).
- **Commands:**

```bash
uv run ofs counties                        # download, keep the 36 Oregon counties, write the full-resolution file
uv run ofs simplify-counties --percent 5   # make the web-sized file and update the provenance
```

The full-resolution layer is about 8.5 MB and stays local in `data/raw/geo/`; the committed file is simplified for display only. The provenance file records the source, terms, steps and checksums.

**Using a different boundary file:** any method works if the result meets the same contract: 36 Oregon county polygons in WGS84 longitude/latitude, with `fips` ("41" plus the county code) and `name` properties, no larger than 1 MB. The tests check the names, the count and the size. If you substitute a source, update `docs/data-sources.md` and the provenance file with the new source, license and steps.

CI (GitHub Actions) runs the same three checks on every push to `main` and on pull requests.

### Proposing reasons from a PDF with a local model (optional)

Needs [Ollama](https://ollama.com) running on this computer with `qwen3:30b-instruct` pulled (`ollama pull qwen3:30b-instruct`; use the instruct tag, the plain `qwen3:30b` tag is thinking-only). Source PDFs stay local.

```
uv run ofs extract data/raw/<file>.pdf --doc-id <document-id> [--pages 23 | 20-25]
```

Writes `<doc-id>.candidates.json` and `<doc-id>.manifest.json` to `data/local/extract/` (git-ignored). Candidates are uncoded and not hand-checked; a person assigns categories and verifies them. Every quote must be found word for word on its page, or it is rejected (kept in the output for audit). The manifest records the pipeline commit, prompt checksum, model digest, settings, input checksum and an output checksum. The prompt is `prompts/extract-reasons-v1.txt`.

Only a model server on this computer is used. Cloud models (names ending `-cloud`) are refused unless you type a confirmation phrase, or pass `--allow-cloud` in an unattended run; you are then responsible for any personal information sent. To turn Ollama's cloud feature off, set `{"disable_ollama_cloud": true}` in `~/.ollama/server.json` (create it if missing) or set `OLLAMA_NO_CLOUD=1`, and restart Ollama.

## Data model
`project -> proceeding -> document -> reason`. Local proceedings record what a county decided; appeal proceedings record what a reviewing body (for example LUBA) did. Each coded reason has a category from `data/taxonomy/reasons.yaml`, a verbatim quote, and a PDF page number. See `docs/methodology.md` for the rules and the decision log.

Source PDFs are kept locally and are not published. The repo holds structured data, quotes with page references, and a manifest of document checksums.

## Project layout
- `src/oregon_farmland_solar/` – application code (Google-style docstrings, enforced by ruff)
- `tests/` – tests (write the test first)
- `data/taxonomy/` – reason taxonomy (versioned YAML)
- `data/records/` – structured records (JSON)
- `data/geo/` – derived county boundary layer (GeoJSON) and its provenance file; the unmodified download stays in `data/raw/geo/`
- `_site/` – staged Pages output from `ofs stage-site` (git-ignored)
- `site/` – the static website; `site/data/site-data.json` is generated by `ofs site-data`
- `data/synthetic/` – invented demo records (JSON), generated by `ofs synth`; never mixed with real records
- `data/raw/` – source PDFs and other originals (git-ignored, kept locally; see `docs/data-sources.md`)
- `prompts/` – versioned model prompts (their checksums go in run manifests)
- `data/local/` – local-only outputs, e.g. machine-extracted candidates (git-ignored)
- `data/processed/` – derived datasets
- `docs/methodology.md` – decision record: why analyses and data choices were made
- `docs/data-sources.md` – where every dataset came from

## Security notes
This repository is public. Never commit API keys, tokens, or credentials. Keep them in a local `.env` file (git-ignored) and read them from environment variables.

Branch protection for `main` (pull request required, `test` check must pass, no force pushes or deletion) is documented in `.github/rulesets/protect-main.json`. GitHub does not read this file automatically; it is a copy of the ruleset imported in the repository settings, so update both together.

## Known limitations
- Schema, taxonomy and validators exist; three sample projects (Marion, Yamhill, Jackson) are coded; all three are hand-checked.
- The reason taxonomy is a draft based on three sample projects.
- Quote verification and personal-information checks run locally against the source PDFs, which are not published.
- Coverage is limited to the records obtained (see Scope and coverage): county records are approvals only, and appeal and court outcomes are incomplete.
- The synthetic records use arbitrary distributions (counties, acreage, outcomes, reasons). They show layout and behavior only and say nothing about real Oregon decisions.
- _TODO: add geographic and permit-record limitations as they are discovered._
