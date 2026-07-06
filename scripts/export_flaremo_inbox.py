#!/usr/bin/env python3
"""Export tagged FlareMo memos into a monthly Obsidian inbox note."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_time(value: str) -> datetime:
    value = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def memo_time(memo: dict) -> datetime:
    for key in ("updateTime", "updatedTs", "createTime", "createdTs", "createdAt", "updatedAt"):
        value = memo.get(key)
        if isinstance(value, str):
            return parse_time(value)
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000 if value > 10_000_000_000 else value, timezone.utc)
    return datetime.min.replace(tzinfo=timezone.utc)


def memo_id(memo: dict) -> str:
    value = memo.get("name") or memo.get("id") or memo.get("uid")
    return str(value)


def memo_content(memo: dict) -> str:
    value = memo.get("content") or memo.get("text") or memo.get("message") or ""
    return html.unescape(str(value)).strip()


def has_tag(content: str, tags: set[str]) -> bool:
    if not tags:
        return True
    found = {tag.lower() for tag in re.findall(r"(?<!\w)#([\w/-]+)", content)}
    return bool(found & tags)


def load_cursor(path: Path) -> set[str]:
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(item) for item in data.get("exported", [])}


def save_cursor(path: Path, exported: set[str]) -> None:
    path.write_text(json.dumps({"exported": sorted(exported)}, indent=2) + "\n", encoding="utf-8")


def fetch_memos(url: str, client_id: str | None, client_secret: str | None) -> list[dict]:
    req = urllib.request.Request(url.rstrip("/") + "/api/v1/memos")
    if client_id:
        req.add_header("CF-Access-Client-Id", client_id)
    if client_secret:
        req.add_header("CF-Access-Client-Secret", client_secret)

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if isinstance(data, list):
        return data
    for key in ("memos", "items", "data"):
        if isinstance(data.get(key), list):
            return data[key]
    raise ValueError("FlareMo response did not contain a memo list.")


def format_entry(memo: dict) -> str:
    stamp = memo_time(memo).astimezone().strftime("%Y-%m-%d %H:%M")
    body = memo_content(memo)
    return f"\n## {stamp}\n\n{body}\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    url = os.environ["FLAREMO_URL"]
    tags = {tag.strip().lstrip("#").lower() for tag in os.environ.get("FLAREMO_TAGS", "").split(",") if tag.strip()}
    vault = Path(os.environ.get("OBSIDIAN_VAULT", ROOT)).expanduser()
    inbox_dir = vault / os.environ.get("FLAREMO_INBOX_DIR", "Inbox")
    cursor_path = vault / ".flaremo-export-cursor.json"

    exported = load_cursor(cursor_path)
    new_memos = [
        memo
        for memo in fetch_memos(
            url,
            os.environ.get("FLAREMO_ACCESS_CLIENT_ID"),
            os.environ.get("FLAREMO_ACCESS_CLIENT_SECRET"),
        )
        if memo_id(memo) not in exported and has_tag(memo_content(memo), tags)
    ]
    new_memos.sort(key=memo_time)

    if args.dry_run:
        print(f"{len(new_memos)} memo(s) would be exported.")
        return

    inbox_dir.mkdir(parents=True, exist_ok=True)
    touched: set[Path] = set()
    for memo in new_memos:
        month = memo_time(memo).astimezone().strftime("%Y-%m")
        out = inbox_dir / f"FlareMo {month}.md"
        if not out.exists():
            out.write_text(f"# FlareMo {month}\n", encoding="utf-8")
        with out.open("a", encoding="utf-8") as fh:
            fh.write(format_entry(memo))
        exported.add(memo_id(memo))
        touched.add(out)

    save_cursor(cursor_path, exported)
    for path in sorted(touched):
        print(path)
    print(f"exported {len(new_memos)} memo(s)")


if __name__ == "__main__":
    main()
