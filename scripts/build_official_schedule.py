#!/usr/bin/env python3
"""Build a strictly date-bounded pilot feed from reviewed official calendars.

This does NOT scrape or infer official approval. The input is manually checked.
"""
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "official_schedule_sources.json"
OUTPUT = ROOT / "data" / "official_schedule.json"
REQUIRED = ("id", "name", "category", "date", "end", "time", "place",
            "access", "why", "trivia", "url", "source_type", "access_scope",
            "source_checked_on", "editorial_status")
ALLOWED = {"スポーツ", "天文・自然", "テレビ"}
ALLOWED_SCOPE = {"国内視聴可", "日本で観測可能", "関東現地参加"}
MAX_HORIZON = 60


def build_schedule(source: dict, today: dt.date | None = None) -> dict:
    today = today or dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    if not isinstance(source.get("events"), list):
        raise ValueError("events array missing")
    out, seen = [], set()
    for event in source["events"]:
        if not all(isinstance(event.get(key), str) and event[key].strip() for key in REQUIRED):
            raise ValueError("Incomplete reviewed event record")
        if event["id"] in seen:
            raise ValueError("Duplicate event ID")
        seen.add(event["id"])
        if event["editorial_status"] != "manual_official_checked":
            continue
        if event["category"] not in ALLOWED or event["access_scope"] not in ALLOWED_SCOPE:
            continue
        if not event["url"].startswith("https://"):
            raise ValueError("Official source URL must be HTTPS")
        try:
            start = dt.date.fromisoformat(event["date"])
            end = dt.date.fromisoformat(event["end"])
            checked = dt.date.fromisoformat(event["source_checked_on"])
        except ValueError as exc:
            raise ValueError("Invalid date in reviewed event") from exc
        if end < start or checked > today or checked < today - dt.timedelta(days=90):
            continue
        if end < today or start > today + dt.timedelta(days=MAX_HORIZON):
            continue
        out.append({k: event[k] for k in REQUIRED})
    out.sort(key=lambda x: (x["date"], x["id"]))
    return {
        "data_kind": "manually_verified_official_calendar_pilot",
        "as_of_jst": today.isoformat(),
        "horizon_days": MAX_HORIZON,
        "note": "記事公開日ではなく公式予定日。出典確認済みの手動シード。テレビ一般番組は検証できるまで未掲載。掲載前に最新の公式情報を再確認してください。",
        "events": out,
    }


def main():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    schedule = build_schedule(source)
    OUTPUT.write_text(json.dumps(schedule, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Official calendar pilot: {len(schedule['events'])} upcoming records")


if __name__ == "__main__":
    main()
