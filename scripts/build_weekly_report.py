#!/usr/bin/env python3
"""Build a weekly team leaderboard report from a saved Golfstat HTML page."""

from __future__ import annotations

import csv
import html
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_HTML = ROOT / "raw" / "golfstat_team_26416.html"
CSV_OUT = ROOT / "data" / "team_leaderboard_26416.csv"
REPORT_OUT = ROOT / "reports" / "weekly_analysis_26416_2026-06-04.md"
SOURCE_URL = "https://results.golfstat.com/public/leaderboards/gsnav.cfm?pg=team&tid=26416"


@dataclass(frozen=True)
class TeamRow:
    position: str
    movement: str
    team: str
    to_par: int
    thru: str
    today: int
    r1: int
    r2: int
    r3: int
    total: int

    @property
    def final_round_change(self) -> int:
        return self.r3 - self.r2

    @property
    def best_round(self) -> int:
        return min(self.r1, self.r2, self.r3)

    @property
    def worst_round(self) -> int:
        return max(self.r1, self.r2, self.r3)

    @property
    def consistency_range(self) -> int:
        return self.worst_round - self.best_round


def strip_tags(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def signed_int(value: str) -> int:
    value = value.strip()
    if value in {"E", "Even"}:
        return 0
    return int(value)


def parse_meta(page: str) -> dict[str, str]:
    title = re.search(r"<title>(.*?)</title>", page, re.S)
    tournament = re.search(r'pg=participants&tid=26416[^"]*".*?>(.*?)</a>', page, re.S)
    course_line = re.search(r"<div>(Carolina Country Club.*?)</div>", page)
    location = re.search(r"<div>\s*(Spartanburg, SC US)\s*</div>", page)
    event_dates = re.search(r"<div style=\"display:inline-block;\" align=\"center\">\s*(.*?)\s*</div>", page, re.S)

    return {
        "page_title": strip_tags(title.group(1)) if title else "Golfstat Team Leaderboard",
        "tournament": strip_tags(tournament.group(1)) if tournament else "The Carolina Cup",
        "course": strip_tags(course_line.group(1)) if course_line else "",
        "location": strip_tags(location.group(1)) if location else "",
        "event_dates": strip_tags(event_dates.group(1)) if event_dates else "",
        "source_url": SOURCE_URL,
    }


def parse_rows(page: str) -> list[TeamRow]:
    row_blocks = re.findall(
        r'<div style="background-color:#ffffff;white-space:nowrap;">(.*?)<div id="team\d+"',
        page,
        re.S,
    )
    rows: list[TeamRow] = []

    for block in row_blocks:
        team_match = re.search(r'getTeamScorecard\(([^)]*)\)">(.*?)</a>', block, re.S)
        if not team_match:
            continue

        pos_cells = re.findall(r'<div style="inline-block;text-align:center">(.*?)</div>', block, re.S)
        position = strip_tags(pos_cells[0]) if pos_cells else ""

        if "moveup.png" in block:
            move_number = re.search(r"moveup\.png[^>]*>\s*(\d+)", block, re.S)
            movement = f"Up {move_number.group(1) if move_number else ''}".strip()
        elif "movedown.png" in block:
            move_number = re.search(r"movedown\.png[^>]*>\s*(\d+)", block, re.S)
            movement = f"Down {move_number.group(1) if move_number else ''}".strip()
        else:
            movement = "No change"

        score_values = re.findall(
            r'<div style="white-space:nowrap;text-align:right;width:2\.75em;" align="center">(.*?)</div>',
            block,
            re.S,
        )
        if len(score_values) != 2:
            raise ValueError(f"Expected to-par and today values for {team_match.group(2)!r}")

        thru_match = re.search(
            r'<div style="display:inline-block;border:1px solid silver; width:60px;padding:2px; text-align:center;">\s*([^<]+?)\s*</div>\s*'
            r'<div style="display:inline-block;border:1px solid silver; width:60px;padding:2px; text-align:center;"><div style="white-space:nowrap;text-align:right;width:2\.75em;"',
            block,
            re.S,
        )
        rounds = [int(value) for value in re.findall(r"<round_score>(\d+)</round_score>", block)]
        if len(rounds) != 3:
            raise ValueError(f"Expected three round scores for {team_match.group(2)!r}")

        rows.append(
            TeamRow(
                position=position,
                movement=movement,
                team=strip_tags(team_match.group(2)),
                to_par=signed_int(strip_tags(score_values[0])),
                thru=strip_tags(thru_match.group(1)) if thru_match else "F",
                today=signed_int(strip_tags(score_values[1])),
                r1=rounds[0],
                r2=rounds[1],
                r3=rounds[2],
                total=sum(rounds),
            )
        )

    if not rows:
        raise ValueError("No team rows found in Golfstat HTML.")
    return rows


def write_csv(rows: list[TeamRow]) -> None:
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    with CSV_OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "position",
                "movement",
                "team",
                "to_par",
                "thru",
                "today",
                "r1",
                "r2",
                "r3",
                "total",
                "final_round_change",
                "consistency_range",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "position": row.position,
                    "movement": row.movement,
                    "team": row.team,
                    "to_par": row.to_par,
                    "thru": row.thru,
                    "today": row.today,
                    "r1": row.r1,
                    "r2": row.r2,
                    "r3": row.r3,
                    "total": row.total,
                    "final_round_change": row.final_round_change,
                    "consistency_range": row.consistency_range,
                }
            )


def fmt_score(value: int) -> str:
    if value > 0:
        return f"+{value}"
    return str(value)


def build_report(meta: dict[str, str], rows: list[TeamRow]) -> str:
    leader = rows[0]
    runner_up = rows[1]
    best_today = min(rows, key=lambda row: row.today)
    best_round = min((score, row.team, round_name) for row in rows for round_name, score in [("R1", row.r1), ("R2", row.r2), ("R3", row.r3)])
    biggest_final_round_gain = min(rows, key=lambda row: row.final_round_change)
    most_consistent = sorted(rows, key=lambda row: (row.consistency_range, row.total))[:3]
    final_round_average = sum(row.r3 for row in rows) / len(rows)
    total_spread = rows[-1].total - rows[0].total
    under_par = [row for row in rows if row.to_par < 0]

    lines: list[str] = [
        f"# Weekly Analysis Report: {meta['tournament']}",
        "",
        f"- Source: {meta['source_url']}",
        f"- Event: {meta['event_dates']}",
        f"- Venue: {meta['course']}, {meta['location']}",
        f"- Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- Dataset: {len(rows)} teams, final team leaderboard",
        "",
        "## Executive Summary",
        "",
        f"{leader.team} won at {fmt_score(leader.to_par)} ({leader.total}), finishing {runner_up.total - leader.total} shots ahead of {runner_up.team}. "
        f"The winning profile was built on back-to-back 276s in R2 and R3 after opening with 292, a 16-shot improvement from R1 to R2 that separated UAB from the field.",
        "",
        f"The event was top-heavy: {len(under_par)} teams finished under par, while the full leaderboard spread was {total_spread} shots from first to last. "
        f"{best_today.team} had the strongest final-day score at {fmt_score(best_today.today)} ({best_today.r3}), and the field averaged {final_round_average:.1f} in R3.",
        "",
        "## Leaderboard",
        "",
        "| Pos | Team | To Par | R1 | R2 | R3 | Total | Today | Movement |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]

    for row in rows:
        lines.append(
            f"| {row.position} | {row.team} | {fmt_score(row.to_par)} | {row.r1} | {row.r2} | {row.r3} | {row.total} | {fmt_score(row.today)} | {row.movement} |"
        )

    lines.extend(
        [
            "",
            "## Performance Signals",
            "",
            f"- Winning edge: {leader.team} gained {runner_up.total - leader.total} shots on second-place {runner_up.team}.",
            f"- Best single team round: {best_round[1]} shot {best_round[0]} in {best_round[2]}.",
            f"- Best final round: {best_today.team} shot {best_today.r3}, listed as {fmt_score(best_today.today)} for the day.",
            f"- Biggest R2-to-R3 improvement: {biggest_final_round_gain.team} improved by {-biggest_final_round_gain.final_round_change} shots from R2 to R3.",
            f"- Most consistent teams: {', '.join(f'{row.team} ({row.consistency_range}-shot range)' for row in most_consistent)}.",
            "",
            "## Team Notes",
            "",
            f"- {leader.team}: Closed with 276 after another 276 in R2. The final two rounds were the tournament's decisive scoring band.",
            f"- {runner_up.team}: Finished second at {fmt_score(runner_up.to_par)} despite a final-round 287. Strong R1/R2 scoring kept pressure on the winner.",
            "- Western Carolina: Finished third with steady scoring of 290-286-288 and the second-best consistency profile among podium teams.",
            "- Mercer: Opened with the field's best R1 score of 282, but a 298 in R2 created too much ground to recover.",
            "- Connecticut: Lost ground with a final-round 304, showing how costly R3 volatility was.",
            "- Jacksonville: Rebounded from 309 in R2 to 293 in R3, the largest round-to-round improvement on the final day.",
            "",
            "## Next Analysis Steps",
            "",
            "- Add player leaderboard data from the same tournament ID to connect team movement to individual counting scores.",
            "- Compare this event against other weekly tournament IDs to identify repeatable team trends rather than one-event form.",
            "- Track R1-to-R3 scoring ranges as a stability metric for future weekly reports.",
        ]
    )

    return "\n".join(lines) + "\n"


def main() -> None:
    page = RAW_HTML.read_text(encoding="utf-8", errors="replace")
    meta = parse_meta(page)
    rows = parse_rows(page)
    rows.sort(key=lambda row: row.total)
    write_csv(rows)
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.write_text(build_report(meta, rows), encoding="utf-8")
    print(f"Wrote {CSV_OUT}")
    print(f"Wrote {REPORT_OUT}")


if __name__ == "__main__":
    main()
