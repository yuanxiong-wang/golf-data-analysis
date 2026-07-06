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

## Import FlareMo Inbox

```sh
export FLAREMO_URL="https://your-flaremo.example.com"
export FLAREMO_TAGS="gkzid,wiaa"
export FLAREMO_ACCESS_CLIENT_ID="..."
export FLAREMO_ACCESS_CLIENT_SECRET="..."
python3 scripts/export_flaremo_inbox.py
```

Writes tagged notes to `Inbox/FlareMo YYYY-MM.md`. Set `OBSIDIAN_VAULT` to export into another vault.
