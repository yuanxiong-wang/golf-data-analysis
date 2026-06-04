# Golf Data Analysis

Obsidian vault for golf leaderboard data, analysis scripts, and weekly reports.

## Current Contents

- `raw/` stores downloaded source pages.
- `data/` stores parsed datasets.
- `reports/` stores Markdown analysis reports.
- `scripts/` stores reproducible parsing and report-generation scripts.

## Rebuild Latest Report

```sh
python3 scripts/build_weekly_report.py
```

The current report uses Golfstat tournament ID `26416` for The Carolina Cup.
