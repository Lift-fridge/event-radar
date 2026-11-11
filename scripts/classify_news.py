"""Classify RSS titles without external APIs or a permanent name blacklist."""

import re

RECOMMEND = "推薦候補"
REVIEW = "要確認"
EXCLUDE = "対象外"

REPORT = re.compile(r"ライブレポート|オフィシャルライブレポート|開催後|振り返り|舞台写真.*公開|公演.*レポート")
ANIME_ANNOUNCEMENT = re.compile(
    r"(?:TVアニメ|アニメ|anime).*(?:ティザー|PV|ビジュアル|放送時期|キャスト|スタッフ|新作映像|新シーズン)"
    r"|(?:ティザー|PV|ビジュアル|放送時期|キャスト|スタッフ|新作映像|新シーズン).*(?:TVアニメ|アニメ|anime)"
)
FAN_EVENT = re.compile(r"ファン(?:ミーティング|ミ|イベント)|お渡し会|リリースイベント|声優.*(?:イベント|ライブ)")
ORDINARY_LIVE = re.compile(r"ワンマン|(?:ライブ|コンサート|ツアー).*(?:開催|決定)|(?:開催|決定).*(?:ライブ|コンサート|ツアー)")
MAJOR = re.compile(
    r"映画祭|国際映画祭|フェスティバル|特別番組|スペシャル|展覧会|企画展|博物館|科学館|皆既|流星|花火大会|"
    r"ワールドカップ|オリンピック|全国大会|決勝|再結成|復活|周年|記念公演"
)
EVENT = re.compile(r"開催|開幕|開演|公演|上映|映画祭|フェス|ライブ|コンサート|大会|出場|放送|配信|展覧会|企画展|予約|応募|チケット|来日|初放送|初公開")


def classify_title(title: str) -> tuple[str, str]:
    """Return (status, reason) from an RSS title.

    Entity names are deliberately not used as exclusion rules. The same artist or
    series may be relevant for a major event and irrelevant for a routine article.
    """
    title = title.strip()
    if REPORT.search(title):
        return EXCLUDE, "開催後のレポート・振り返り記事のため"
    if FAN_EVENT.search(title):
        return EXCLUDE, "コアなファン向けのイベント告知のため"
    if ANIME_ANNOUNCEMENT.search(title):
        return EXCLUDE, "アニメの通常の新作・放送告知で、イベント情報としての独自性が低いため"
    if ORDINARY_LIVE.search(title) and not MAJOR.search(title):
        return EXCLUDE, "通常のライブ・ツアー告知で、推薦基準の主要イベントに該当しないため"
    if MAJOR.search(title):
        return RECOMMEND, "主要イベントまたは幅広い関心が見込める題材を含むため"
    if EVENT.search(title):
        return REVIEW, "イベントの可能性はあるが、知名度・開催条件の追加確認が必要なため"
    return EXCLUDE, "イベント開催を示す情報が不足しているため"
