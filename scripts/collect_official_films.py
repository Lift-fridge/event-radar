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


class AnchorParser(HTMLParser):
    """Extract linked film listing card text rather than assuming movie headings."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.active = None
        self.ignore = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style", "noscript"):
            self.ignore += 1
        if tag == "a" and self.active is None and not self.ignore:
            self.active = {"href": attrs.get("href"), "text": [], "image_alt": []}
        if tag == "img" and self.active is not None and attrs.get("alt"):
            self.active["image_alt"].append(attrs["alt"])

    def handle_data(self, data):
        if self.active is not None and not self.ignore:
            self.active["text"].append(" ".join(data.split()))

    def handle_endtag(self, tag):
        if tag == "a" and self.active is not None:
            text = " ".join(x for x in self.active["text"] if x).strip()
            if not text:
                text = " ".join(self.active["image_alt"]).strip()
            self.links.append({"text": text, "href": self.active["href"]})
            self.active = None
        if tag in ("script", "style", "noscript") and self.ignore:
            self.ignore -= 1



class TohoCardParser(HTMLParser):
    """Pair official Toho film-card title and its adjacent release subtext."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.titles = 0
        self.pairs = []
        self.current_title = None
        self.collecting = None
        self.text = []

    def handle_starttag(self, tag, attrs):
        cls = dict(attrs).get("class", "").split()
        if tag == "h3" and "works-link-001__title" in cls:
            self.titles += 1
            self.current_title = None
            self.collecting = "title"
            self.text = []
        elif tag == "p" and "works-link-001__subtext" in cls:
            self.collecting = "date"
            self.text = []

    def handle_data(self, data):
        if self.collecting:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == "h3" and self.collecting == "title":
            self.current_title = " ".join(" ".join(self.text).split())
            self.collecting = None
        elif tag == "p" and self.collecting == "date":
            details = " ".join(" ".join(self.text).split())
            if self.current_title:
                self.pairs.append((self.current_title, details))
            self.current_title = None
            self.collecting = None

def release_day(text):
    match = DATE.search(text)
    if not match:
        return None
    try:
        return dt.date(*map(int, match.groups()))
    except ValueError:
        return None


def normalized_title(title):
    return re.sub(r"[\\s　『』「」【】()（）・:：]|^(?:映画|劇場版)", "", title).lower().replace("公開", "")


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
    parser = TohoCardParser()
    parser.feed(raw)
    found = []
    for title, details in parser.pairs:
        if not title or len(title) > 110 or "ブルーレイ" in details or "DVD" in details:
            continue
        day = release_day(details)
        if day:
            found.append(make_record("東宝", url, title, day.isoformat()))
    unique = {(r["name"], r["date"]): r for r in found}
    return list(unique.values()), parser.titles > 0


def parse_warner(raw, url):
    html = AnchorParser()
    html.feed(raw)
    found = []
    for link in html.links:
        value = link["text"]
        match = WARNER.search(value)
        if not match or "ブルーレイ" in value or "DVD" in value:
            continue
        day = release_day(match.group(1))
        if day:
            found.append(make_record("ワーナー・ブラザース", url, match.group(2), day.isoformat()))
    unique = {(r["name"], r["date"]): r for r in found}
    return list(unique.values()), bool(html.links) and any(
        "近日公開" in x["text"] for x in html.links)

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
