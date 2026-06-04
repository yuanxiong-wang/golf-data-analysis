#!/usr/bin/env python3
"""Create source inventories from public Golfstat homepage/subpage snapshots."""

from __future__ import annotations

import csv
import html
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
DATA = ROOT / "data"
REPORTS = ROOT / "reports"
HOME_HTML = RAW / "golfstat_homepage.html"
EVENTLIST_HTML = RAW / "golfstat_eventlist_individual.html"
ROBOTS_TXT = RAW / "golfstat_robots.txt"
MINIBOARDS = RAW / "miniboards"

HOME_URL = "https://www.golfstat.com/"
SCORE_URL = "https://score.golfstat.com/"


def clean_text(value: str) -> str:
    value = value.replace("\\'", "'")
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_homepage_miniboards(page: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    pattern = re.compile(
        r'<div class="dimpled_column" title="(?P<title>[^"]*)">.*?'
        r'<div class="liveTableType">(?P<gender>[^<]*)</div>.*?'
        r"<script src='(?P<src>https://score\.golfstat\.com/miniboards/(?P<kind>[tp])leaderboard_(?P<tid>\d+)\.html)'></script>",
        re.S,
    )
    seen: set[tuple[str, str]] = set()

    for match in pattern.finditer(page):
        board_type = "team" if match.group("kind") == "t" else "player"
        key = (match.group("tid"), board_type)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "tournament_id": match.group("tid"),
                "tournament_name": clean_text(match.group("title")),
                "gender": clean_text(match.group("gender")),
                "board_type": board_type,
                "miniboard_url": match.group("src"),
                "results_url": f"https://results.golfstat.com/public/leaderboards/gsnav.cfm?pg={board_type}&tid={match.group('tid')}",
            }
        )
    return rows


def parse_eventlist_categories(page: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for type_code, name in re.findall(r'eventlist\.cfm\?type=([A-Z])"[^>]*>(.*?)</a>', page, re.S):
        rows.append(
            {
                "type_code": type_code,
                "category": clean_text(name),
                "url": urljoin(SCORE_URL, f"eventlist.cfm?type={type_code}"),
            }
        )
    return rows


def parse_eventlist_events(page: str, type_code: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    pattern = re.compile(
        r'<td class="tableEntry" nowrap>(?P<dates>.*?)</td>\s*'
        r'<td class="tableEntry">\s*'
        r'<a href="\./eventlist\.cfm\?type=(?P<type>[A-Z])&eventid=(?P<eventid>\d+)">\s*'
        r"(?P<event>.*?)</a>",
        re.S,
    )
    for match in pattern.finditer(page):
        if match.group("type") != type_code:
            continue
        rows.append(
            {
                "type_code": type_code,
                "event_id": match.group("eventid"),
                "dates": clean_text(match.group("dates")),
                "event": clean_text(match.group("event")),
                "url": urljoin(SCORE_URL, f"eventlist.cfm?type={type_code}&eventid={match.group('eventid')}"),
            }
        )
    return rows


def parse_saved_miniboards() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(MINIBOARDS.glob("*leaderboard_*.html")):
        text = path.read_text(encoding="utf-8", errors="replace")
        tid_match = re.search(r"leaderboard_(\d+)\.html", path.name)
        board_type = "team" if path.name.startswith("tleaderboard") else "player"
        if not tid_match:
            continue
        tid = tid_match.group(1)

        meta = re.search(
            r"<strong><a[^>]*>(?P<event>.*?)</a></strong><br>(?P<dates>.*?)<br><strong>(?P<label>.*?)</strong>",
            text,
            re.S,
        )
        event = clean_text(meta.group("event")) if meta else ""
        dates = clean_text(meta.group("dates")) if meta else ""
        label = clean_text(meta.group("label")) if meta else ""

        leader_rows = re.findall(
            r"<tr><td align=right class=copy>(?P<pos>.*?)</td>"
            r"<td style=padding-left:10px nowrap class=copy>(?P<name>.*?)</td>"
            r"<td align=right class=copy style=padding-right:10px nowrap>(?P<score>.*?)</td></tr>",
            text,
            re.S,
        )
        for pos, name, score in leader_rows:
            rows.append(
                {
                    "tournament_id": tid,
                    "event": event,
                    "dates": dates,
                    "board_type": board_type,
                    "label": label,
                    "position": clean_text(pos),
                    "name": clean_text(name),
                    "score": clean_text(score),
                    "source_file": str(path.relative_to(ROOT)),
                }
            )
    return rows


def build_report(
    miniboard_rows: list[dict[str, str]],
    categories: list[dict[str, str]],
    events: list[dict[str, str]],
    leaders: list[dict[str, str]],
) -> str:
    tournament_ids = sorted({row["tournament_id"] for row in miniboard_rows})
    team_boards = sum(1 for row in miniboard_rows if row["board_type"] == "team")
    player_boards = sum(1 for row in miniboard_rows if row["board_type"] == "player")
    robots = ROBOTS_TXT.read_text(encoding="utf-8", errors="replace").strip() if ROBOTS_TXT.exists() else ""

    lines = [
        "# Golfstat Public Data Inventory",
        "",
        f"- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- Homepage source: {HOME_URL}",
        "- Event-list sample source: https://score.golfstat.com/eventlist.cfm?type=I",
        f"- Robots check: {'allows public crawling' if 'Disallow:' in robots and 'User-agent: *' in robots else 'review manually'}",
        "",
        "## What I Found",
        "",
        f"- Homepage exposes {len(miniboard_rows)} miniboard links across {len(tournament_ids)} tournament IDs.",
        f"- Homepage board split: {team_boards} team boards and {player_boards} player boards.",
        f"- Event-list navigation exposes {len(categories)} public categories.",
        f"- Junior Golf event-list sample contains {len(events)} events.",
        f"- Saved miniboard samples contain {len(leaders)} leader rows.",
        "",
        "## Public Source Layers",
        "",
        "| Layer | Data Available | Best Use |",
        "|---|---|---|",
        "| Homepage miniboards | Current/upcoming tournament IDs, event names, gender, team/player board links | Build a live tournament watchlist |",
        "| Miniboard snippets | Top 10 team/player leaders for a tournament | Quick weekly scoreboard summary |",
        "| Full leaderboard pages | Detailed team/player leaderboard for one tournament ID | Deep event analysis report |",
        "| Event-list pages | Historical event catalogs by category/type | Build archive indexes |",
        "| Rankings/schedule pages | Potential team/player ranking and schedule data | Separate crawler after scope decision |",
        "",
        "## Event Categories From Score Subpage",
        "",
        "| Type | Category | URL |",
        "|---|---|---|",
    ]
    for row in categories:
        lines.append(f"| {row['type_code']} | {row['category']} | {row['url']} |")

    lines.extend(
        [
            "",
            "## First 10 Homepage Tournament Boards",
            "",
            "| Tournament ID | Event | Gender | Boards |",
            "|---:|---|---|---|",
        ]
    )
    grouped: dict[str, dict[str, str | set[str]]] = {}
    for row in miniboard_rows:
        entry = grouped.setdefault(
            row["tournament_id"],
            {"event": row["tournament_name"], "gender": row["gender"], "boards": set()},
        )
        assert isinstance(entry["boards"], set)
        entry["boards"].add(row["board_type"])
    for tid in tournament_ids[:10]:
        entry = grouped[tid]
        boards = ", ".join(sorted(entry["boards"]))  # type: ignore[arg-type]
        lines.append(f"| {tid} | {entry['event']} | {entry['gender']} | {boards} |")

    lines.extend(
        [
            "",
            "## Suggested Next Direction",
            "",
            "Choose one of these before I crawl deeper:",
            "",
            "1. Current weekly report engine: download all homepage miniboards and summarize active events.",
            "2. Deep tournament engine: for selected tournament IDs, download full team/player leaderboards and analyze round-by-round performance.",
            "3. Historical archive: crawl event-list categories and build searchable event catalogs by division/category.",
            "4. Rankings/schedule module: inspect Golfstat rankings and schedule pages separately and design parsers for those tables.",
            "",
            "My recommendation: start with option 1, then use option 2 for any event that matters.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    home = HOME_HTML.read_text(encoding="utf-8", errors="replace")
    eventlist = EVENTLIST_HTML.read_text(encoding="utf-8", errors="replace")

    miniboard_rows = parse_homepage_miniboards(home)
    categories = parse_eventlist_categories(eventlist)
    events = parse_eventlist_events(eventlist, "I")
    leaders = parse_saved_miniboards()

    write_csv(
        DATA / "golfstat_homepage_miniboards.csv",
        miniboard_rows,
        ["tournament_id", "tournament_name", "gender", "board_type", "miniboard_url", "results_url"],
    )
    write_csv(
        DATA / "golfstat_eventlist_categories.csv",
        categories,
        ["type_code", "category", "url"],
    )
    write_csv(
        DATA / "golfstat_eventlist_junior_golf.csv",
        events,
        ["type_code", "event_id", "dates", "event", "url"],
    )
    write_csv(
        DATA / "golfstat_miniboard_leaders_sample.csv",
        leaders,
        ["tournament_id", "event", "dates", "board_type", "label", "position", "name", "score", "source_file"],
    )

    REPORTS.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS / "golfstat_data_inventory_2026-06-04.md"
    report_path.write_text(build_report(miniboard_rows, categories, events, leaders), encoding="utf-8")

    print(f"homepage miniboards: {len(miniboard_rows)}")
    print(f"event categories: {len(categories)}")
    print(f"junior events: {len(events)}")
    print(f"sample leader rows: {len(leaders)}")
    print(f"wrote {report_path}")


if __name__ == "__main__":
    main()
