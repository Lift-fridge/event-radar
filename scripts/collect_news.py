#!/usr/bin/env python3
"""Fetch public RSS metadata and classify leads; this does not approve events."""
import datetime as dt
import email.utils
import hashlib
import json
import pathlib
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

from classify_news import EXCLUDE, classify_title

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "discovery.json"
SOURCES = (
    ("SPICE", "https://spice-api.eplus.jp/rss/articles/latest.xml?encoded=1"),
    ("音楽ナタリー", "https://natalie.mu/music/feed/news"),
    ("映画ナタリー", "https://natalie.mu/eiga/feed/news"),
    ("マイナビニュース", "https://news.mynavi.jp/rss/index.rdf"),
)
POSITIVE = "開催|開幕|開演|公演|上映|映画祭|フェス|ライブ|コンサート|大会|出場|放送|配信|ドラマ|展覧会|企画展|予約|応募|先行販売|チケット|来日|初回|初放送|初公開"
NEGATIVE = "中止|延期|開催終了|閉幕|振り返り|レビュー|発売した|販売終了|決算|株価|企業買収|スマホ新製品"
UA = "EventRadar-Research/0.1 (RSS metadata; no republishing of article bodies)"
NS = {"atom": "http://www.w3.org/2005/Atom"}


def node_text(node, names):
    for name in names:
        value = node.findtext(name)
        if value:
            return value.strip()
    return ""


def iso_date(value):
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        return parsed.astimezone(dt.timezone.utc).isoformat() if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc).isoformat()
    except (TypeError, ValueError):
        pass
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(dt.timezone.utc).isoformat()
    except ValueError:
        return None


def read_feed(source, url):
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"})
    with urllib.request.urlopen(request, timeout=18) as response:
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("feed too large")
    root = ET.fromstring(raw)
    result = []
    for node in root.iter():
        if node.tag.split("}")[-1] not in ("item", "entry"):
            continue
        title = node_text(node, ["title", "{http://www.w3.org/2005/Atom}title"])
        link = node_text(node, ["link", "{http://purl.org/rss/1.0/}link"])
        if not link:
            atom_link = node.find("atom:link", NS)
            if atom_link is not None:
                link = atom_link.get("href", "")
        if not title or not link or not link.startswith(("https://", "http://")):
            continue
        published = node_text(node, ["pubDate", "{http://purl.org/dc/elements/1.1/}date", "{http://www.w3.org/2005/Atom}published", "{http://www.w3.org/2005/Atom}updated"])
        timestamp = iso_date(published)
        if not re.search(POSITIVE, title) or re.search(NEGATIVE, title):
            continue
        status, reason = classify_title(title)
        result.append({
            "id": hashlib.sha256(link.encode()).hexdigest()[:20],
            "source": source,
            "title": title[:180],
            "url": link,
            "article_published_at": timestamp,
            "event_date": None,
            "status": status,
            "classification_reason": reason,
            "confirmed": False,
        })
    return result


def main():
    collected = []
    errors = []
    successes = 0
    for name, url in SOURCES:
        try:
            items = read_feed(name, url)
            collected.extend(items)
            successes += 1
            print(f"{name}: {len(items)} candidates")
        except Exception as exc:
            errors.append({"source": name, "error_type": type(exc).__name__})
            print(f"{name}: {type(exc).__name__}", file=sys.stderr)
    if successes == 0:
        print("All feeds failed; previous data preserved.", file=sys.stderr)
        return 1
    now = dt.datetime.now(dt.timezone.utc)
    seen = set()
    fresh = []
    for item in sorted(collected, key=lambda x: x["article_published_at"] or "", reverse=True):
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        stamp = item["article_published_at"]
        if stamp:
            age = now - dt.datetime.fromisoformat(stamp)
            if age > dt.timedelta(days=14) or age < -dt.timedelta(days=1):
                continue
        fresh.append(item)
        if len(fresh) == 60:
            break
    counts = {status: sum(item["status"] == status for item in fresh) for status in ("推薦候補", "要確認", EXCLUDE)}
    payload = {
        "updated_at": now.isoformat(timespec="seconds"),
        "data_kind": "classified_unverified_news_leads",
        "message": "記事の公開日はイベント開催日ではありません。開催日時と日本での視聴・参加方法を公式情報で確認するまで、確定イベント一覧には掲載しません。",
        "successful_sources": successes,
        "source_count": len(SOURCES),
        "errors": errors,
        "classification_counts": counts,
        "items": fresh,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUTPUT.with_suffix(".json.tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(OUTPUT)
    print(f"Saved {len(fresh)} classified news leads.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
