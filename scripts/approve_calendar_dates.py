"""Fail-closed promotion of noteworthy astronomical calendar dates.

Only the extreme ("極大") date of meteor showers may be auto-displayed.
The official NAOJ Japan-facing monthly calendar is authoritative for the
calendar *date*, not for the local observing weather or hourly visibility.
"""
import datetime as dt
import re
from urllib.parse import urlsplit

METEOR_PEAK = re.compile(r"^[^\s/]{1,24}流星群が極大$")
NAOJ_MONTH = re.compile(r"^/astro/sky/(\d{4})/(\d{2})\.html$")
MAX_DAYS = 60


def approved_meteor_events(discovery: dict, today: dt.date, existing: list[dict]) -> list[dict]:
    """Promote source-verified calendar dates only, never other discoveries."""
    try:
        generated = dt.date.fromisoformat(discovery["generated_at"][:10])
    except (KeyError, TypeError, ValueError):
        return []
    if generated > today or generated < today - dt.timedelta(days=2):
        return []

    valid_sources = {
        r.get("url")
        for r in discovery.get("source_reports", [])
        if r.get("source") == "NAOJ" and r.get("status") == "ok"
    }
    already = {(e["name"], e["date"]) for e in existing}
    accepted = []
    for event in discovery.get("items", []):
        source = event.get("source_page_url", "")
        parsed = urlsplit(source)
        month = NAOJ_MONTH.fullmatch(parsed.path)
        if (parsed.scheme != "https" or parsed.hostname != "www.nao.ac.jp"
                or parsed.query or parsed.fragment or month is None
                or source not in valid_sources or event.get("source_type") != "国立天文台ほしぞら情報"
                or event.get("official_url") != source
                or event.get("publishable") is not False
                or not METEOR_PEAK.fullmatch(event.get("name", ""))
                or event.get("verification", {}).get("status") != "unverified"):
            continue
        try:
            day = dt.date.fromisoformat(event["date"])
            end = dt.date.fromisoformat(event["end"])
        except (KeyError, ValueError, TypeError):
            continue
        if (day != end or day < today or day > today + dt.timedelta(days=MAX_DAYS)
                or (day.year, day.month) != (int(month[1]), int(month[2]))):
            continue
        identity = (event["name"], event["date"])
        if identity in already:
            continue
        already.add(identity)
        accepted.append({
            "id": event["id"],
            "name": event["name"],
            "category": "天文・自然",
            "date": event["date"],
            "end": event["end"],
            "time": "極大日（見頃の時間帯は公式情報を参照）",
            "place": "日本の夜空（観測条件は場所や天候によって異なります）",
            "access": "肉眼で観測できる場合があります。見頃・月明かり・天気は公式情報を確認してください",
            "why": "流星群の極大日を事前に知り、観察する機会を逃さないため。",
            "trivia": "極大日時と日本で見やすい時間帯は一致しないことがあります。",
            "url": source,
            "source_type": "国立天文台公式月別カレンダー",
            "access_scope": "国内天文カレンダー",
            "source_checked_on": today.isoformat(),
            "editorial_status": "auto_verified_calendar_date",
        })
    return accepted
