#!/usr/bin/env python3
"""Build Junior Golf focused datasets and report from saved Golfstat pages."""

from __future__ import annotations

import csv
import html
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
DATA = ROOT / "data"
REPORTS = ROOT / "reports"
MINIBOARDS = RAW / "miniboards"
JUNIOR_PAGES = RAW / "junior_event_pages"


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


def signed_score(value: str) -> int | None:
    value = value.strip()
    if value in {"", "-", "W", "WD"}:
        return None
    if value == "E":
        return 0
    return int(value)


def numeric_value(value: str) -> int | None:
    value = value.strip()
    if value and value.lstrip("+-").isdigit():
        return int(value)
    return None


def add_total_audit(row: dict[str, str]) -> None:
    round_values = [numeric_value(row.get(key, "")) for key in ["r1", "r2", "r3", "r4"]]
    numeric_rounds = [value for value in round_values if value is not None]
    total = numeric_value(row.get("total", ""))
    row["round_sum"] = str(sum(numeric_rounds)) if numeric_rounds else ""
    row["total_delta"] = str(total - sum(numeric_rounds)) if total is not None and numeric_rounds else ""


def parse_page_meta(text: str, title_prefix: str) -> dict[str, str]:
    title = re.search(rf"<title>{title_prefix} - (.*?) -", text, re.S | re.I)
    course_with_par = re.search(r"<div>\s*([^<]+?)\s*<br/>\s*Par\s+([^<]+?)\s*</div>", text, re.S)
    course_single_line = re.search(r"<div>\s*([^<]*?Par\s+\d+\s+-\s+\d+\s+Yards)\s*</div>", text, re.S)
    location = re.search(r"<div>\s*([^<]*(?:, [A-Z]{2} US|, [A-Z]{2}|JP JP))\s*</div>", text)
    event_dates = re.search(r'<div style="display:inline-block;" align="center">\s*(.*?)\s*</div>', text, re.S)

    if course_with_par:
        course = f"{clean_text(course_with_par.group(1))} - Par {clean_text(course_with_par.group(2))}"
    elif course_single_line:
        course = clean_text(course_single_line.group(1))
    else:
        course = ""

    return {
        "event": clean_text(title.group(1)) if title else "",
        "course": course,
        "location": clean_text(location.group(1)) if location else "",
        "dates": clean_text(event_dates.group(1)) if event_dates else "",
    }


def parse_event_archive() -> list[dict[str, str]]:
    path = DATA / "golfstat_eventlist_junior_golf.csv"
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        year_match = re.search(r"(20\d{2})", row["dates"])
        row["year"] = year_match.group(1) if year_match else ""
        event_lower = row["event"].lower()
        if "elite invitational" in event_lower:
            family = "The Elite Invitational"
        elif "toyota" in event_lower:
            family = "Toyota Junior World Cup"
        elif "orange bowl" in event_lower:
            family = "Junior Orange Bowl"
        elif "dustin johnson" in event_lower:
            family = "Dustin Johnson World Junior"
        elif "wiaa" in event_lower:
            family = "WIAA"
        elif "sage valley" in event_lower:
            family = "Sage Valley"
        else:
            family = "Other"
        row["event_family"] = family
    return rows


def parse_event_detail_pages() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    pattern = re.compile(
        r'<td class="tableEntry" nowrap>(?P<dates>.*?)</td>\s*'
        r'<td class="tableEntry"><a href="public/index\.cfm\?tournament_id=(?P<tid>\d+)">(?P<tournament>.*?)</a></td>\s*'
        r'<td class="tableEntry">\s*(?P<location>.*?)</td>\s*'
        r'<td class="tableEntry" nowrap>(?P<host>.*?)</td>\s*'
        r'<td class="tableEntry">(?P<status>.*?)</td>',
        re.S,
    )
    for path in sorted(JUNIOR_PAGES.glob("event_*.html")):
        event_id = re.search(r"event_(\d+)\.html", path.name)
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in pattern.finditer(text):
            rows.append(
                {
                    "event_id": event_id.group(1) if event_id else "",
                    "tournament_id": match.group("tid"),
                    "dates": clean_text(match.group("dates")),
                    "tournament": clean_text(match.group("tournament")),
                    "location": clean_text(match.group("location")),
                    "host": clean_text(match.group("host")),
                    "status": clean_text(match.group("status")),
                    "event_detail_file": str(path.relative_to(ROOT)),
                    "full_player_url": f"https://results.golfstat.com/public/leaderboards/gsnav.cfm?pg=player&tid={match.group('tid')}",
                    "full_team_url": f"https://results.golfstat.com/public/leaderboards/gsnav.cfm?pg=team&tid={match.group('tid')}",
                }
            )
    return rows


def parse_homepage_junior_boards() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with (DATA / "golfstat_homepage_miniboards.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if "JUNIOR" in row["gender"].upper() or row["gender"].lower().startswith("hs "):
                rows.append(row)
    return rows


def parse_miniboard_leaders(junior_tids: set[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(MINIBOARDS.glob("*leaderboard_*.html")):
        tid_match = re.search(r"leaderboard_(\d+)\.html", path.name)
        if not tid_match or tid_match.group(1) not in junior_tids:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        board_type = "team" if path.name.startswith("tleaderboard") else "player"
        meta = re.search(
            r"<strong><a[^>]*>(?P<event>.*?)</a></strong><br>(?P<dates>.*?)<br><strong>(?P<label>.*?)</strong>",
            text,
            re.S,
        )
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
                    "tournament_id": tid_match.group(1),
                    "event": clean_text(meta.group("event")) if meta else "",
                    "dates": clean_text(meta.group("dates")) if meta else "",
                    "board_type": board_type,
                    "label": clean_text(meta.group("label")) if meta else "",
                    "position": clean_text(pos),
                    "name": clean_text(name),
                    "score": clean_text(score),
                    "source_file": str(path.relative_to(ROOT)),
                }
            )
    return rows


def parse_full_player_page(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    tid = re.search(r"tid=(\d+)", text)
    meta = parse_page_meta(text, "player")
    blocks = re.findall(r'<div style="color:black;">(.*?)<div id="Player', text, re.S)

    rows: list[dict[str, str]] = []
    for block in blocks:
        pos_cells = re.findall(
            r'<div style="display:inline-block;border:1px solid silver; width:40px;padding:2px; text-align:center;">(.*?)</div>',
            block,
            re.S,
        )
        wide_cells = re.findall(
            r'<div style="display:inline-block;border:1px solid silver; width:195px;padding:2px 2px 2px 5px; text-align:left;">(.*?)</div>',
            block,
            re.S,
        )
        scores = re.findall(
            r'<div style="white-space:nowrap;text-align:right;width:2\.5em;" align="center">\s*(.*?)\s*</div>',
            block,
            re.S,
        )
        rounds = [clean_text(value) for value in re.findall(r"<round_score>(.*?)</round_score>", block, re.S)]
        if len(pos_cells) < 2 or len(wide_cells) < 2 or len(scores) < 2:
            continue
        row = {
            "tournament_id": tid.group(1) if tid else "",
            "event": meta["event"],
            "course": meta["course"],
            "location": meta["location"],
            "dates": meta["dates"],
            "position": clean_text(pos_cells[0]),
            "player": clean_text(wide_cells[0]),
            "affiliation": clean_text(wide_cells[1]),
            "to_par": clean_text(scores[0]),
            "today": clean_text(scores[1]),
            "r1": rounds[0] if len(rounds) > 0 else "",
            "r2": rounds[1] if len(rounds) > 1 else "",
            "r3": rounds[2] if len(rounds) > 2 else "",
            "r4": rounds[3] if len(rounds) > 3 else "",
            "total": clean_text(pos_cells[-1]),
            "source_file": str(path.relative_to(ROOT)),
        }
        add_total_audit(row)
        rows.append(row)
    return rows


def parse_full_team_page(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    tid = re.search(r"tid=(\d+)", text)
    meta = parse_page_meta(text, "Team")
    blocks = re.findall(
        r'<div style="background-color:#ffffff;white-space:nowrap;">(.*?)<div id="team\d+"',
        text,
        re.S,
    )

    rows: list[dict[str, str]] = []
    for block in blocks:
        team_match = re.search(r'getTeamScorecard\([^)]*\)">(.*?)</a>', block, re.S)
        pos = re.search(r'<div style="inline-block;text-align:center">(.*?)</div>', block, re.S)
        scores = re.findall(
            r'<div style="white-space:nowrap;text-align:right;width:2\.75em;" align="center">(.*?)</div>',
            block,
            re.S,
        )
        rounds = [clean_text(value) for value in re.findall(r"<round_score>(.*?)</round_score>", block, re.S)]
        total_match = re.findall(r'<div class="hideDiv" style="border:1px solid silver; width:60px;padding:2px; text-align:center;">\s*([^<\s][^<]*?)\s*</div>', block, re.S)
        if not team_match or not pos or len(scores) < 2:
            continue
        row = {
            "tournament_id": tid.group(1) if tid else "",
            "event": meta["event"],
            "course": meta["course"],
            "location": meta["location"],
            "dates": meta["dates"],
            "position": clean_text(pos.group(1)),
            "team": clean_text(team_match.group(1)),
            "to_par": clean_text(scores[0]),
            "today": clean_text(scores[1]),
            "r1": rounds[0] if len(rounds) > 0 else "",
            "r2": rounds[1] if len(rounds) > 1 else "",
            "r3": rounds[2] if len(rounds) > 2 else "",
            "r4": rounds[3] if len(rounds) > 3 else "",
            "total": clean_text(total_match[-1]) if total_match else "",
            "source_file": str(path.relative_to(ROOT)),
        }
        add_total_audit(row)
        rows.append(row)
    return rows


def parse_full_samples() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    player_rows: list[dict[str, str]] = []
    for path in sorted(JUNIOR_PAGES.glob("player_*.html")):
        player_rows.extend(parse_full_player_page(path))
    team_rows: list[dict[str, str]] = []
    for path in sorted(JUNIOR_PAGES.glob("team_*.html")):
        team_rows.extend(parse_full_team_page(path))
    return player_rows, team_rows


def score_sort_key(row: dict[str, str]) -> tuple[int, int]:
    parsed = signed_score(row["score"])
    return (parsed if parsed is not None else 999, int(re.sub(r"\D", "", row["position"]) or 999))


def build_report(
    archive: list[dict[str, str]],
    details: list[dict[str, str]],
    boards: list[dict[str, str]],
    mini: list[dict[str, str]],
    full_players: list[dict[str, str]],
    full_teams: list[dict[str, str]],
) -> str:
    years = [int(row["year"]) for row in archive if row["year"]]
    family_counts = Counter(row["event_family"] for row in archive)
    board_tids = sorted({row["tournament_id"] for row in boards})
    mini_by_event: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in mini:
        mini_by_event[f"{row['event']} [{row['tournament_id']}] ({row['board_type']})"].append(row)

    boys = [row for row in full_players if row["tournament_id"] == "29467"]
    girls = [row for row in full_players if row["tournament_id"] == "29468"]
    team_leader = full_teams[0] if full_teams else None

    lines = [
        "# Junior Golf Deep Dive",
        "",
        f"- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "- Section source: https://score.golfstat.com/eventlist.cfm?type=I",
        "- Homepage source: https://www.golfstat.com/",
        "",
        "## Scope",
        "",
        f"- Junior archive records parsed: {len(archive)}",
        f"- Archive year range: {min(years) if years else 'n/a'}-{max(years) if years else 'n/a'}",
        f"- Event-detail pages sampled: {len(details)}",
        f"- Homepage Junior board links: {len(boards)} across {len(board_tids)} tournament IDs",
        f"- Junior miniboard leader rows parsed: {len(mini)}",
                f"- Full current player leaderboard rows parsed: {len(full_players)}",
                f"- Full current team leaderboard rows parsed: {len(full_teams)}",
        "",
        "## Archive Shape",
        "",
        "| Event family | Events |",
        "|---|---:|",
    ]
    for family, count in family_counts.most_common():
        lines.append(f"| {family} | {count} |")

    lines.extend(
        [
            "",
            "## Current Junior Boards On Homepage",
            "",
            "| Tournament ID | Event | Gender | Board | Full leaderboard |",
            "|---:|---|---|---|---|",
        ]
    )
    for row in boards:
        lines.append(
            f"| {row['tournament_id']} | {row['tournament_name']} | {row['gender']} | {row['board_type']} | {row['results_url']} |"
        )

    player_counts = Counter(row["tournament_id"] for row in full_players)
    team_counts = Counter(row["tournament_id"] for row in full_teams)
    board_names = {row["tournament_id"]: row["tournament_name"] for row in boards}
    total_deltas = [row for row in full_players + full_teams if row.get("total_delta") not in {"", "0"}]
    lines.extend(
        [
            "",
            "## Full Leaderboard Coverage",
            "",
            "| Tournament ID | Event | Player rows | Team rows |",
            "|---:|---|---:|---:|",
        ]
    )
    for tid in sorted(set(player_counts) | set(team_counts)):
        lines.append(f"| {tid} | {board_names.get(tid, '')} | {player_counts.get(tid, 0)} | {team_counts.get(tid, 0)} |")

    if total_deltas:
        lines.extend(
            [
                "",
                "## Data Quality Notes",
                "",
                f"- {len(total_deltas)} row has a displayed total that differs from the visible round-score sum; the CSV keeps both `total` and `round_sum`, with the difference in `total_delta`.",
            ]
        )

    lines.extend(["", "## Top Miniboard Leaders", ""])
    for label, rows in sorted(mini_by_event.items()):
        lines.append(f"### {label}")
        lines.append("")
        lines.append("| Pos | Name | Score |")
        lines.append("|---:|---|---:|")
        for row in sorted(rows, key=score_sort_key)[:10]:
            lines.append(f"| {row['position']} | {row['name']} | {row['score']} |")
        lines.append("")

    if boys:
        leader = boys[0]
        lines.extend(
            [
                "## Full Leaderboard: Elite Invitational Boys",
                "",
                f"- Event: {leader['event']}",
                f"- Venue: {leader['course']}, {leader['location']}",
                f"- Dates: {leader['dates']}",
                f"- Rows parsed: {len(boys)}",
                f"- Leader: {leader['player']} ({leader['affiliation']}) at {leader['to_par']} with rounds {leader['r1']}-{leader['r2']}-{leader['r3']} for {leader['total']}.",
                "",
            ]
        )
    if girls:
        leader = girls[0]
        lines.extend(
            [
                "## Full Leaderboard: Elite Invitational Girls",
                "",
                f"- Event: {leader['event']}",
                f"- Venue: {leader['course']}, {leader['location']}",
                f"- Dates: {leader['dates']}",
                f"- Rows parsed: {len(girls)}",
                f"- Leader: {leader['player']} ({leader['affiliation']}) at {leader['to_par']} with rounds {leader['r1']}-{leader['r2']}-{leader['r3']} for {leader['total']}.",
                "",
            ]
        )
    if team_leader:
        lines.extend(
            [
                "## Full Team Leaderboard: Toyota Junior Boys",
                "",
                f"- Event: {team_leader['event']}",
                f"- Venue: {team_leader['course']}, {team_leader['location']}",
                f"- Dates: {team_leader['dates']}",
                f"- Rows parsed: {len(full_teams)}",
                f"- Leader: {team_leader['team']} at {team_leader['to_par']} with rounds {team_leader['r1']}-{team_leader['r2']}-{team_leader['r3']}-{team_leader['r4']} for {team_leader['total']}.",
                "",
            ]
        )

    lines.extend(
        [
            "## Data Model Recommendation",
            "",
            "- Use `event_id` for Junior archive navigation on `score.golfstat.com`.",
            "- Use `tournament_id` for analytical leaderboards on `results.golfstat.com`.",
            "- Maintain both IDs when available because an archive event can be the clean calendar object, while tournament IDs are the scoring objects.",
            "- For Junior reports, prioritize player leaderboards first; many Junior events are individual-only, while some international events also provide team boards.",
            "",
            "## Next Crawl Step",
            "",
            "The next useful expansion is to turn these current full leaderboards into event-by-event analysis pages, starting with Elite Invitational Boys/Girls and Toyota Junior World Cup Boys/Girls.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    archive = parse_event_archive()
    details = parse_event_detail_pages()
    boards = parse_homepage_junior_boards()
    mini = parse_miniboard_leaders({row["tournament_id"] for row in boards})
    full_players, full_teams = parse_full_samples()

    write_csv(
        DATA / "junior_golf_event_archive.csv",
        archive,
        ["type_code", "event_id", "dates", "event", "url", "year", "event_family"],
    )
    write_csv(
        DATA / "junior_golf_event_details_sample.csv",
        details,
        [
            "event_id",
            "tournament_id",
            "dates",
            "tournament",
            "location",
            "host",
            "status",
            "event_detail_file",
            "full_player_url",
            "full_team_url",
        ],
    )
    write_csv(
        DATA / "junior_golf_homepage_boards.csv",
        boards,
        ["tournament_id", "tournament_name", "gender", "board_type", "miniboard_url", "results_url"],
    )
    write_csv(
        DATA / "junior_golf_miniboard_leaders.csv",
        mini,
        ["tournament_id", "event", "dates", "board_type", "label", "position", "name", "score", "source_file"],
    )
    write_csv(
        DATA / "junior_golf_full_player_leaderboards_current.csv",
        full_players,
        [
            "tournament_id",
            "event",
            "course",
            "location",
            "dates",
            "position",
            "player",
            "affiliation",
            "to_par",
            "today",
            "r1",
            "r2",
            "r3",
            "r4",
            "total",
            "round_sum",
            "total_delta",
            "source_file",
        ],
    )
    write_csv(
        DATA / "junior_golf_full_team_leaderboards_current.csv",
        full_teams,
        [
            "tournament_id",
            "event",
            "course",
            "location",
            "dates",
            "position",
            "team",
            "to_par",
            "today",
            "r1",
            "r2",
            "r3",
            "r4",
            "total",
            "round_sum",
            "total_delta",
            "source_file",
        ],
    )

    REPORTS.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS / "junior_golf_deep_dive_2026-06-04.md"
    report_path.write_text(build_report(archive, details, boards, mini, full_players, full_teams), encoding="utf-8")

    print(f"archive rows: {len(archive)}")
    print(f"event detail rows: {len(details)}")
    print(f"homepage junior boards: {len(boards)}")
    print(f"miniboard leaders: {len(mini)}")
    print(f"full current player rows: {len(full_players)}")
    print(f"full current team rows: {len(full_teams)}")
    print(f"wrote {report_path}")


if __name__ == "__main__":
    main()
