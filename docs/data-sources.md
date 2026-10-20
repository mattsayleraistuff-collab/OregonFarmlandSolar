# Data sources

One row per dataset. Raw files live in `data/raw/` (git-ignored); record how to re-obtain them here.

| File name | Name | Publisher | URL | Retrieved | License / terms | SHA-256 | Notes |
|-----------|------|-----------|-----|-----------|-----------------|---------|-------|
| `MarionCo_Staff_Report_CU22-041.pdf` | Marion Co. staff report, CU 22-041 (2 pp) | Marion County Planning Division | not recorded | not recorded | public record | `139c9aadacf92b753f20c285619add4ea6870948561e4376e7cb062030c87875` | Local copy only; manually downloaded sample |
| `LUBA_23045_2023.pdf` | Silver Creek Solar, LLC v. Marion County, LUBA No. 2023-045 (18 pp) | Oregon LUBA | not recorded | not recorded | public record | `a161030180f441f10ec3b5f87efc9022b4b6e00b40e6c11afb9ccda450573722` | Local copy only; manually downloaded sample |
| `LUBA_18009_2018.pdf` | Yamhill Creek Solar, LLC v. Yamhill County, LUBA No. 2018-009 (43 pp) | Oregon LUBA | not recorded | not recorded | public record | `879718643b38b3adfddbc674c4ad768c4ed8351e85b05eb02d0029db1d446e23` | Local copy only; manually downloaded sample |
| `LUBA_17066_2017.pdf` | 1000 Friends of Oregon v. Jackson County (OR Solar 7), LUBA No. 2017-066, 76 Or LUBA 270 (37 pp) | Oregon LUBA | not recorded | not recorded | public record | `050ca34bb4dd1b6295b5c42fa6b4a1f37df9e5ce9701812a99dba1fdfe952fbc` | Local copy only; manually downloaded sample |
| `LUBA_17066_2019_remand.pdf` | 1000 Friends of Oregon v. Jackson County, LUBA No. 2017-066, on remand (5 pp) | Oregon LUBA | not recorded | not recorded | public record | `ef928732e4142183ae3551f6a3b9921fd75fb9ea40a6560df1d58ec907a98a06` | Local copy only; manually downloaded sample |
| `blm-or-county-boundaries.geojson` | BLM OR County Boundaries Polygon Hub (Oregon and Washington counties) | Bureau of Land Management, Oregon State Office, via Oregon GeoHub | https://geohub.oregon.gov/datasets/51d396ec311d449fa2f6cb1141d496f2_1 (query service: see `data/geo/oregon-counties.provenance.json`) | not built yet | Provided 'as is'; cite BLM; describe modifications and do not imply BLM endorsement; not a legal document or survey; BLM may update without notice | recorded in `data/geo/oregon-counties.provenance.json` once `uv run ofs counties` has run | Original kept unmodified in `data/raw/geo/` (local). Derived `data/geo/oregon-counties.geojson` keeps the 36 Oregon counties, adds `fips` and `name`, and is simplified to 5% of vertices for display (mapshaper 0.7.92); the full-resolution copy stays local. Source covers Washington too, so counties are filtered by the `OR` code prefix, not by name. |

## File names and case numbers
LUBA file names in `data/raw/` use the case number with the dash removed, then the decision year: `LUBA_23045_2023.pdf` is **LUBA No. 2023-045** (case year 2023, number 045). The first digits are the year the appeal was filed, so a remand years later keeps the original number (`LUBA_17066_2017.pdf` and `LUBA_17066_2019_remand.pdf` are both LUBA No. 2017-066).

| File name | Project | Record / case |
|-----------|---------|---------------|
| `MarionCo_Staff_Report_CU22-041.pdf` | Silver Creek Solar (Marion) | Staff report, CU 22-041 |
| `LUBA_23045_2023.pdf` | Silver Creek Solar (Marion) | LUBA No. 2023-045 |
| `LUBA_18009_2018.pdf` | Yamhill Creek Solar (Yamhill) | LUBA No. 2018-009 |
| `LUBA_17066_2017.pdf` | OR Solar 7 (Jackson) | LUBA No. 2017-066 |
| `LUBA_17066_2019_remand.pdf` | OR Solar 7 (Jackson) | LUBA No. 2017-066, on remand |
| `6.3.4.pdf` | none | LUBA digest, background only (no reasons) |
| `Item_6_Exhibit_2_1k Friends.pdf` | none | Advocacy letter, background only (no reasons) |

Each real document in `data/records/` has a `file_name` field and a `sha256`; the checksum is what actually links a record to a file, so renaming a PDF does not break verification.
