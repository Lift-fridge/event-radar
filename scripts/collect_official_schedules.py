#!/usr/bin/env python3
"""Collect future official schedule leads without auto-publishing them."""

import datetime as dt
import hashlib
import html
import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "official_discovery.json"
MANUAL_SOURCE = ROOT / "data" / "official_schedule.json"
JST = dt.timezone(dt.timedelta(hours=9))
UA = "EventRadar-OfficialSchedule/0.1 (metadata only)"
ASTRONOMY_EVENT = re.compile(r"流星群|月食|日食|彗星|火星が地球に最接近|惑星.*接近|オーロラ")
DATE_TOKEN = re.compile(r"(?:(\d{4})/)?(\d{1,2})/(\d{1,2})")
DAY_TOKEN = re.compile(r"(\d{1,2})日")
CANCELLED = re.compile(r"中止|延期")


class TableParser(HTMLParser):
    """Extract table rows while tolerating unrelated markup changes."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.row = None
        self.cell = None
        self.link = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = {"text": [], "url": None}
        elif tag == "a" and self.cell is not None and self.cell["url"] is None:
            self.link = attrs.get("href")
            self.cell["url"] = self.link

    def handle_data(self, data):
        if self.cell is not None:
            self.cell["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "a":
            self.link = None
        elif tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append({"text": " ".join(self.cell["text"]).strip(), "url": self.cell["url"]})
            self.cell = None
        elif tag == "tr" and self.row:
            self.rows.append(self.row)
            self.row = None


def parse_jfa_date(value, year):
    matches = list(DATE_TOKEN.finditer(value))
    if not matches:
        return None, None

    def convert(match, fallback_year):
        event_year = int(match.group(1) or fallback_year)
        return dt.date(event_year, int(match.group(2)), int(match.group(3)))

    start = convert(matches[0], year)
    end = convert(matches[1], start.year if len(matches) > 1 else year) if len(matches) > 1 else start
    if len(matches) > 1 and not matches[1].group(1) and end < start:
        end = end.replace(year=end.year + 1)
    return start, end


def parse_naoj_date(value, year, month):
    days = [int(x) for x in DAY_TOKEN.findall(value)]
    if not days:
        return None, None
    start = dt.date(year, month, days[0])
    end = dt.date(year, month, days[1]) if len(days) > 1 else start
    return start, end


def make_id(prefix, name, date, url):
    return f"{prefix}-{hashlib.sha256(f'{name}|{date}|{url}'.encode()).hexdigest()[:16]}"


def jfa_events(document, url, year):
    parser = TableParser()
    parser.feed(document)
    events = []
    for row in parser.rows:
        if len(row) < 4:
            continue
        start, end = parse_jfa_date(row[0]["text"], year)
        if not start:
            continue
        name = row[1]["text"]
        score = row[2]["text"]
        whole = " ".join(cell["text"] for cell in row)
        if not name or (score and score not in ("-", "–")) or CANCELLED.search(whole):
            continue
        opponent = row[3]["text"]
        place = row[4]["text"] if len(row) > 4 else None
        display_name = f"{name} vs {opponent}" if opponent and opponent != "未定" else name
        event_url = row[1]["url"] or url
        events.append({
            "id": make_id("jfa", display_name, start.isoformat(), event_url),
            "name": display_name,
            "category": "スポーツ",
            "date": start.isoformat(),
            "end": end.isoformat(),
            "time": None,
            "place": place or None,
            "access": None,
            "official_url": event_url,
            "source_type": "JFA公式試合日程",
            "source_checked_on": None,
            "status": "要確認",
            "publishable": False,
            "verification": {
                "status": "unverified",
                "broadcast_or_streaming_in_japan": None,
                "cancellation_status": "pending",
            },
            "reason": "JFA公式予定。試合日程・開催場所は取得済みだが、日本での放送・配信と中止・延期状況を確認するまで掲載しない。",
        })
    return events


def naoj_events(document, url, year, month):
    parser = TableParser()
    parser.feed(document)
    events = []
    for row in parser.rows:
        if len(row) < 2:
            continue
        start, end = parse_naoj_date(row[0]["text"], year, month)
        detail = row[1]["text"]
        if not start or not ASTRONOMY_EVENT.search(detail):
            continue
        name = re.sub(r"^\d{1,2}時頃、?\s*", "", detail).split("（", 1)[0].strip()
        time_match = re.search(r"\d{1,2}時頃", detail)
        events.append({
            "id": make_id("naoj", name, start.isoformat(), url),
            "name": name or detail,
            "category": "天文・自然",
            "date": start.isoformat(),
            "end": end.isoformat(),
            "time": time_match.group(0) if time_match else None,
            "place": "東京の星空（国立天文台公式ページ）",
            "access": detail,
            "official_url": url,
            "source_type": "国立天文台ほしぞら情報",
            "source_checked_on": None,
            "status": "要確認",
            "publishable": False,
            "verification": {
                "status": "unverified",
                "observation_condition_in_japan": None,
                "cancellation_status": "not_applicable",
            },
            "reason": "国立天文台の月間カレンダーにある天文現象。日本での観測条件・見頃を確認するまで掲載しない。",
        })
    return events


def month_targets(today):
    next_month = (today.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    return [(today.year, today.month), (next_month.year, next_month.month)]


def manual_keys(manual):
    return {(event.get("name"), event.get("date")) for event in manual.get("events", [])}


def collect(today=None, fetcher=None, manual=None):
    today = today or dt.datetime.now(JST).date()
    fetcher = fetcher or fetch_html
    manual = manual or {}
    events, errors, sources_ok = [], [], 0
    urls = [("JFA", f"https://www.jfa.jp/samuraiblue/schedule_result/{year}.html", year) for year in (today.year, today.year + 1)]
    urls += [("NAOJ", f"https://www.nao.ac.jp/astro/sky/{year}/{month:02d}.html", year, month) for year, month in month_targets(today)]
    for source in urls:
        name, url = source[:2]
        try:
            document = fetcher(url)
            sources_ok += 1
            if name == "JFA":
                events.extend(jfa_events(document, url, source[2]))
            else:
                events.extend(naoj_events(document, url, source[2], source[3]))
        except Exception as exc:
            errors.append({"source": name, "url": url, "error_type": type(exc).__name__})
    known = manual_keys(manual)
    deduped = []
    seen = set()
    for event in events:
        identity = (event["name"], event["date"])
        if identity in known or identity in seen or dt.date.fromisoformat(event["end"]) < today:
            continue
        seen.add(identity)
        deduped.append(event)
    return {
        "generated_at": dt.datetime.combine(today, dt.time(), JST).isoformat(timespec="seconds"),
        "data_kind": "official_unverified_schedule_leads",
        "message": "公式ページから取得した予定候補ですが、検証完了まで確定イベント一覧には掲載しません。",
        "source_count": len(urls),
        "successful_sources": sources_ok,
        "source_errors": errors,
        "items": deduped,
    }


def fetch_html(url):
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read(2_000_001)
    if len(body) > 2_000_000:
        raise ValueError("page too large")
    return body.decode("utf-8", errors="strict")


def main():
    manual = json.loads(MANUAL_SOURCE.read_text(encoding="utf-8")) if MANUAL_SOURCE.exists() else {}
    payload = collect(manual=manual)
    if payload["successful_sources"] == 0:
        raise SystemExit("All official sources failed; previous data preserved.")
    temp = OUTPUT.with_suffix(".json.tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(OUTPUT)
    print(f"Official schedule leads: {len(payload['items'])}; source errors: {len(payload['source_errors'])}")


if __name__ == "__main__":
    main()
