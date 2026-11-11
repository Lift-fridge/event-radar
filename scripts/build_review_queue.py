#!/usr/bin/env python3
"""Create a human verification queue from unverified RSS article leads."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "discovery.json"
OUTPUT = ROOT / "data" / "review_queue.json"

PREFECTURES = ("東京都", "神奈川県", "千葉県", "埼玉県")
OUTSIDE_EXAMPLES = ("北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
                    "茨城県", "栃木県", "群馬県", "新潟県", "長野県", "山梨県", "静岡県",
                    "愛知県", "京都府", "大阪府", "兵庫県", "福岡県", "沖縄県", "札幌市", "神戸市")
CHECKS = (
    "公式情報で開催日（記事公開日とは別）を確認",
    "開始・終了時刻、開催地・会場を確認",
    "東京・神奈川・千葉・埼玉で参加可能か、または日本から視聴できるか確認",
    "地上波・配信の有無、BS限定でないことを確認",
    "チケット・応募期限・定員を確認",
    "主要イベントか意外な発見か、掲載理由を確認",
)
PIPELINE_DEFAULTS = {
    "event_group_key": None,
    "priority": "一般",
    "participation_scope": "開催地・視聴方法を要確認",
    "verification": {
        "status": "unverified",
        "official_url": None,
        "event_date": None,
        "start_time": None,
        "end_time": None,
        "location": None,
        "viewing_method": None,
    },
}


def location_hint(title):
    """Conservative text hint; it is never an independently verified venue."""
    target = [p for p in PREFECTURES if p in title]
    elsewhere = [p for p in OUTSIDE_EXAMPLES if p in title]
    if target and elsewhere:
        return "地域混在・要確認"
    if target:
        return "1都3県の地名あり・要確認"
    if elsewhere:
        return "対象外地域の地名あり・配信の有無を要確認"
    return "開催地不明・要確認"


def pipeline_fields(article):
    """Preserve event_pipeline fields while providing old-data defaults."""
    urls = article.get("related_article_urls") or ([article["url"]] if article.get("url") else [])
    verification = article.get("verification")
    if not isinstance(verification, dict):
        verification = PIPELINE_DEFAULTS["verification"].copy()
    return {
        "event_group_key": article.get("event_group_key"),
        "related_article_urls": urls,
        "article_count": article.get("article_count", len(urls) or 1),
        "priority": article.get("priority", PIPELINE_DEFAULTS["priority"]),
        "participation_scope": article.get("participation_scope", PIPELINE_DEFAULTS["participation_scope"]),
        "verification": verification,
    }


def queue_items(discovery):
    """Only nonexcluded candidates. Treat both missing and old 未確認 as review."""
    result = []
    for article in discovery.get("items", []):
        raw_status = article.get("status", "要確認")
        if raw_status == "対象外":
            continue
        status = raw_status if raw_status in ("推薦候補", "要確認") else "要確認"
        title = article.get("title", "")
        result.append({
            "id": article.get("id"),
            "title": title,
            "source": article.get("source"),
            "article_url": article.get("url"),
            "article_published_at": article.get("article_published_at"),
            "candidate_status": status,
            "candidate_reason": article.get("classification_reason", "未検証のため追加確認が必要"),
            "area_hint": location_hint(title),
            **pipeline_fields(article),
            "event_date": None,
            "start_time": None,
            "end_time": None,
            "venue": None,
            "official_source_url": None,
            "availability_in_japan": None,
            "verification_status": "未検証",
            "checks": list(CHECKS),
            "publishable": False,
        })
    return result


def build_queue(discovery):
    return {
        "generated_at": discovery.get("updated_at"),
        "data_kind": "manual_verification_queue",
        "policy": "現地参加は東京・神奈川・千葉・埼玉。全国・海外は日本で視聴可能な場合のみ。花火・地域祭りの網羅は別アプリで扱う。",
        "warning": "地名は見出し上のヒントにすぎません。公式情報の確認なしに掲載しません。",
        "items": queue_items(discovery),
    }


def main():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    if not isinstance(data.get("items"), list):
        raise ValueError("discovery.items must be an array")
    queue = build_queue(data)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Verification queue: {len(queue['items'])} candidates; all unverified.")


if __name__ == "__main__":
    main()
