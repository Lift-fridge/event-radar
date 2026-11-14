#!/usr/bin/env python3
"""Discover Japanese theatrical release dates from official distributor lineups.

Discovery only: no automatic publication, importance inference or showtimes.
"""
import datetime as dt
import hashlib
import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "official_film_discovery.json"
MANUAL = ROOT / "data" / "official_schedule_sources.json"
JST = dt.timezone(dt.timedelta(hours=9))
SOURCES = (
    ("東宝", "https://www.toho.co.jp/movie/lineup/"),
    ("ワーナー・ブラザース", "https://www.warnerbros.co.jp/movie/"),
)
DATE = re.compile(r"(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日\s*(?:（[^）]*）)?\s*(?:全国)?公開")
WARNER = re.compile(r"(20\d{2}年\s*\d{1,2}月\s*\d{1,2}日\s*(?:（[^）]*）)?\s*(?:全国)?公開)\s*映画[『「]([^』」]{1,90})[』」]\s*近日公開")
UA = "EventRadar-FilmDates/0.1 (official title/date metadata only)"
HORIZON = 90


class FilmHTML(HTMLParser):
    """Keep headings and nearby text, without parsing scripts or style."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tokens = []
        self.headings = []
        self.heading = None
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.ignored += 1
        if tag in ("h2", "h3", "h4") and not self.ignored:
            self.heading = [tag, len(self.tokens), []]

    def handle_data(self, data):
        if self.ignored:
            return
        value = " ".join(data.split())
        if value:
            self.tokens.append(value)
            if self.heading is not None:
                self.heading[2].append(value)

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.ignored:
            self.ignored -= 1
        if self.heading is not None and tag == self.heading[0]:
            title = " ".join(self.heading[2]).strip()
            if title:
                self.headings.append((self.heading[1], len(self.tokens), title))
            self.heading = None


def release_day(text):
    match = DATE.search(text)
    if not match:
        return None
    try:
        return dt.date(*map(int, match.groups()))
    except ValueError:
        return None


def normalized_title(title):
    return re.sub(r"[\s　『』「」【】()（）・:：]|^(?:映画|劇場版)", "", title).lower().replace("公開", "")


def make_record(source, page, title, date):
    return {
        "id": "film-" + hashlib.sha256(f"{source}|{title}|{date}".encode()).hexdigest()[:18],
        "name": title,
        "category": "映画",
        "date": date,
        "end": date,
        "time": None,
        "place": "日本国内の劇場（上映館未確認）",
        "access": "上映館・時刻・チケットは未確認",
        "official_url": page,
        "source_page_url": page,
        "source_type": f"{source}公式映画公開予定",
        "status": "要確認",
        "publishable": False,
        "verification": {
            "status": "unverified",
            "japan_theatrical_release_date": "official_lineup_candidate",
            "showtimes": None,
            "editorial_importance": None,
        },
    }


def parse_toho(raw, url):
    html = FilmHTML()
    html.feed(raw)
    found = []
    for _, end, title in html.headings:
        if len(title) > 110 or not title:
            continue
        # The publication date must follow the movie heading before another heading.
        next_start = min((start for start, _, _ in html.headings if start >= end), default=len(html.tokens))
        nearby = " ".join(html.tokens[end:min(next_start, end + 9)])
        day = release_day(nearby)
        if day:
            found.append(make_record("東宝", url, title, day.isoformat()))
    # A page without movie headings is treated as a changed structure.
    return found, bool(html.headings)


def parse_warner(raw, url):
    html = FilmHTML()
    html.feed(raw)
    # Limit the match to individual short neighboring text segments: never
    # pair a release date from one film with the title of another film.
    found = []
    for i in range(len(html.tokens)):
        for size in range(1, 6):
            segment = " ".join(html.tokens[i:i + size])
            if len(segment) > 180:
                break
            m = WARNER.search(segment)
            if not m:
                continue
            day = release_day(m.group(1))
            if day:
                found.append(make_record("ワーナー・ブラザース", url, m.group(2), day.isoformat()))
            break
    unique = {(r["name"], r["date"]): r for r in found}
    return list(unique.values()), bool(html.tokens) and ("近日公開" in " ".join(html.tokens))


def fetch_html(url):
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read(2_000_001)
        charset = response.headers.get_content_charset() or "utf-8"
    if len(body) > 2_000_000:
        raise ValueError("ResponseTooLarge")
    return body.decode(charset, errors="strict")


def filter_events(records, today, manual):
    existing = {(normalized_title(x.get("name", "")), x.get("date"))
                for x in manual.get("events", [])}
    result, seen = [], set()
    for row in records:
        date = dt.date.fromisoformat(row["date"])
        identity = (normalized_title(row["name"]), row["date"])
        if not today <= date <= today + dt.timedelta(days=HORIZON):
            continue
        if identity in existing or identity in seen:
            continue
        seen.add(identity)
        result.append(row)
    result.sort(key=lambda x: (x["date"], x["name"]))
    return result


def collect(today=None, fetcher=None, manual=None):
    today = today or dt.datetime.now(JST).date()
    fetcher = fetcher or fetch_html
    manual = manual or {}
    found, reports = [], []
    for source, url in SOURCES:
        try:
            document = fetcher(url)
            events, structure = (parse_toho(document, url) if source == "東宝"
                                 else parse_warner(document, url))
            status = ("parse_error" if not structure else "ok" if events else "empty")
            reports.append({"source": source, "url": url, "status": status,
                            "extracted_count": len(events)})
            if status == "ok":
                found.extend(events)
        except Exception as exc:
            reports.append({"source": source, "url": url, "status": "fetch_error",
                            "extracted_count": 0, "error_type": type(exc).__name__})
    return {
        "data_kind": "unverified_official_japanese_film_release_candidates",
        "generated_at": dt.datetime.now(JST).isoformat(timespec="seconds"),
        "source_reports": reports,
        "items": filter_events(found, today, manual),
        "message": "日本の配給会社による公開予定の候補。公開日変更・作品の注目度・上映館は未確認。自動掲載しません。",
    }


def main():
    manual = json.loads(MANUAL.read_text(encoding="utf-8")) if MANUAL.exists() else {}
    payload = collect(manual=manual)
    if not any(r["status"] in ("ok", "empty") for r in payload["source_reports"]):
        raise SystemExit("Film sources unavailable; preserving previous discovery.")
    if OUTPUT.exists():
        previous = json.loads(OUTPUT.read_text(encoding="utf-8"))
        failed_pages = {r["url"] for r in payload["source_reports"]
                        if r["status"] in ("parse_error", "fetch_error")}
        kept = [x for x in previous.get("items", [])
                if x.get("source_page_url") in failed_pages]
        payload["items"] = filter_events(payload["items"] + kept,
                                          dt.datetime.now(JST).date(), manual)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(OUTPUT)
    print(f"Film leads: {len(payload['items'])}; sources: {payload['source_reports']}")


if __name__ == "__main__":
    main()
