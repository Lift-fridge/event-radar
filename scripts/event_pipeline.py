"""Conservative grouping and metadata enrichment for RSS event leads."""

import hashlib
import re

from classify_news import EXCLUDE, RECOMMEND, REVIEW

RESULT_OR_GENERAL = re.compile(r"試合結果|結果速報|勝敗|勝利|敗戦|ゲーム|eスポーツ|ソシャゲ|ゲーム実況|政治|事件|事故|株価|企業買収")
YOUTH_STAGE = re.compile(r"2\.5次元|若手俳優|小劇場|アイドル.*舞台|声優.*舞台")
SPORTS_SCHEDULE = re.compile(r"試合予定|対戦カード|試合日程|大会日程|組み合わせ|開幕戦|キックオフ")
TV_FIRST = re.compile(r"初回放送|放送開始|第1話|第１話|初回.*放送")
ASTRONOMY = re.compile(r"皆既月食|部分月食|日食|流星群|ペルセウス座流星群|天文現象|オーロラ")
LOCAL = re.compile(r"東京|東京都|神奈川|横浜|千葉|埼玉|さいたま")
REMOTE = re.compile(r"放送|配信|ライブ配信|生中継|テレビ|ラジオ|ストリーミング")
OVERSEAS = re.compile(r"海外|米国|アメリカ|英国|イギリス|フランス|ドイツ|韓国|台湾|中国|ニューヨーク|ロンドン|パリ")

GROUP_SUFFIX = re.compile(
    r"(?:開催|決定|発表|公開|解禁|到着|登場|実施|予定|詳細|概要|情報|ニュース|コメント|写真|映像|PV|ティザー)"
    r"(?:が|を|の|に|、|・|＆|and|＆)?(?:決定|発表|公開|解禁|到着|公開)?$"
)
EVENT_DETAIL_SUFFIX = re.compile(r"(?:開催概要|上映作品|イベント情報|公演詳細)(?:が|を|の|に)?(?:決定|発表|公開|解禁|到着)?$")
NON_EVENT_WORDS = re.compile(r"[\s　]+|[「」『』【】（）()［］\[\]、。・,:：!！?？…—–-]")


def event_group_key(title: str) -> str:
    """Build a conservative title key; URLs are intentionally ignored."""
    core = title.strip()
    for _ in range(2):
        core = GROUP_SUFFIX.sub("", core)
        core = EVENT_DETAIL_SUFFIX.sub("", core)
    core = NON_EVENT_WORDS.sub("", core).lower()
    return hashlib.sha256(core.encode("utf-8")).hexdigest()[:16]


def classify_scope(title: str) -> str:
    if LOCAL.search(title):
        return "関東現地候補"
    if REMOTE.search(title):
        return "日本からの視聴方法を要確認"
    if OVERSEAS.search(title):
        return "海外開催・日本からの視聴方法を要確認"
    return "開催地・視聴方法を要確認"


def priority_for(title: str) -> str:
    if SPORTS_SCHEDULE.search(title):
        return "スポーツ試合予定"
    if TV_FIRST.search(title):
        return "テレビ番組初回放送"
    if ASTRONOMY.search(title):
        return "天文現象"
    return "一般"


def enrich_item(item: dict) -> dict:
    title = item["title"]
    verification = {
        "status": "unverified",
        "official_url": None,
        "event_date": None,
        "start_time": None,
        "end_time": None,
        "location": None,
        "viewing_method": None,
    }
    return {
        **item,
        "event_group_key": event_group_key(title),
        "priority": priority_for(title),
        "participation_scope": classify_scope(title),
        "verification": verification,
        "related_article_urls": [item["url"]],
    }


def group_news_items(items: list[dict]) -> list[dict]:
    groups: dict[str, dict] = {}
    rank = {EXCLUDE: 0, REVIEW: 1, RECOMMEND: 2}
    for raw in items:
        item = enrich_item(raw)
        key = item["event_group_key"]
        if key not in groups:
            groups[key] = item
            continue
        group = groups[key]
        group["related_article_urls"] = list(dict.fromkeys(group["related_article_urls"] + [item["url"]]))
        group["article_count"] = len(group["related_article_urls"])
        if rank.get(item.get("status"), 0) > rank.get(group.get("status"), 0):
            group["status"] = item["status"]
            group["classification_reason"] = item.get("classification_reason", group.get("classification_reason"))
    for group in groups.values():
        group.setdefault("article_count", len(group["related_article_urls"]))
    return list(groups.values())
