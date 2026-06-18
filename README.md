# Golf Data Analysis

Obsidian vault for golf leaderboard data, analysis scripts, and weekly reports.

## Current Contents

- `raw/` stores downloaded source pages.
- `data/` stores parsed datasets.
- `reports/` stores Markdown analysis reports.
- `scripts/` stores reproducible parsing and report-generation scripts.
- `docs/junior-golf-report/index.html` is the boss-facing HTML report page.

## Start Here

- [Junior Golf HTML Report](docs/junior-golf-report/index.html)
- [GKZID Growth Targeting Brief](reports/gkzid_growth_targeting_2026-06-19.md)
- [Junior Golf Deep Dive](reports/junior_golf_deep_dive_2026-06-04.md)
- [Golfstat Source Inventory](reports/golfstat_data_inventory_2026-06-04.md)

## Rebuild Latest Report

```sh
python3 scripts/build_weekly_report.py
```

The current report uses Golfstat tournament ID `26416` for The Carolina Cup.
