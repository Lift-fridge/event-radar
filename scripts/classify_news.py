"""Classify RSS titles without external APIs or a permanent name blacklist."""

import re

RECOMMEND = "推薦候補"
REVIEW = "要確認"
EXCLUDE = "対象外"
VISIBLE_STATUSES = (RECOMMEND, REVIEW)

REPORT = re.compile(r"ライブレポート|公演レポート|公演.*レポート|開催後|閉幕|終演|振り返り|舞台写真.*公開|"
                    r"開催レポート|開催された|開催されました|をレポート|密着レポート|大迫力ショー.*レポート")
ANIME_ANNOUNCEMENT = re.compile(
    r"(?:TVアニメ|アニメ|anime).*(?:ティザー|PV|ビジュアル|放送時期|キャスト|スタッフ|新作映像|新シーズン)"
    r"|(?:ティザー|PV|ビジュアル|放送時期|キャスト|スタッフ|新作映像|新シーズン).*(?:TVアニメ|アニメ|anime)"
)
FAN_EVENT = re.compile(r"ファン(?:ミーティング|ミ|イベント)|お渡し会|リリースイベント|声優.*(?:イベント|ライブ)")
GAME = re.compile(r"eスポーツ|ｅスポーツ|ゲーム実況|ゲーム大会|ゲームショウ|ゲームショー|東京ゲームショウ|ゲームイベント|ゲーミング大会")
YOUTH_STAGE = re.compile(r"2[.．]5次元|刀剣乱舞|あんさんぶるスターズ|舞台『(?:ヒプノシスマイク|ブルーロック)|ミュージカル『(?:テニスの王子様|刀剣乱舞)")
MATSURI_MAP = re.compile(r"花火大会|地域のお祭り|町内会祭り")
OUTSIDE_LOCATION = re.compile(r"大阪(?:府|市|の)|京都(?:府|市|の)|名古屋(?:市|の)|京都展|大阪展|兵庫県|北海道|福岡(?:県|市|の)|沖縄県|札幌(?:市|の)|神戸(?:市|の)|広島(?:県|市|の)")
TARGET_LOCATION = re.compile(r"東京|神奈川|横浜|川崎|千葉|埼玉|大宮|さいたま|幕張|浦和")
REMOTE = re.compile(r"全国放送|地上波|ネット配信|ライブ配信|生配信|TVer|YouTube配信|NHK総合|BS以外")
SCIENCE = re.compile(r"流星群|月食|日食|惑星|彗星|天体観測|天文現象|星空|接近|観望会|meteor shower|eclipse", re.IGNORECASE)
SPORTS = re.compile(r"日本代表|なでしこジャパン|ワールドカップ|オリンピック|五輪|マスターズ|世界選手権|世界陸上|W杯|決勝戦")
TV = re.compile(r"ドラマ.*(?:初回|放送開始|放送決定|配信開始)|(?:初回|放送開始|放送決定|配信開始).*ドラマ|特別番組|音楽特番|テレビ特番")
ESTABLISHED_MUSIC = re.compile(r"サザンオールスターズ|サザン|松任谷由実|ユーミン|山下達郎|竹内まりや|B.z|スピッツ|Mr\\.Children|ミスチル|ポール・マッカートニー|スティング|U2|米津玄師|Official髭男dism|Mrs\\. GREEN APPLE|MISIA", re.IGNORECASE)
ORDINARY_LIVE = re.compile(r"ワンマン|(?:ライブ|コンサート|ツアー).*(?:開催|決定)|(?:開催|決定).*(?:ライブ|コンサート|ツアー)")
MAJOR = re.compile(
    r"映画祭|国際映画祭|フェスティバル|展覧会|企画展|博物館|科学館|皆既|"
    r"ワールドカップ|オリンピック|全国大会|決勝|再結成|復活|記念公演"
)
EVENT = re.compile(r"開催|開幕|開演|公演|上映|映画祭|フェス|ライブ|コンサート|大会|出場|放送|配信|展覧会|企画展|予約|応募|チケット|来日|初放送|初公開")


def visible_items(items: list[dict]) -> list[dict]:
    """Return reviewable leads; legacy entries without status remain reviewable."""
    return [item for item in items if item.get("status", REVIEW) in VISIBLE_STATUSES]


def classification_counts(items: list[dict]) -> dict[str, int]:
    return {status: sum(item.get("status", REVIEW) == status for item in items) for status in (*VISIBLE_STATUSES, EXCLUDE)}


def classify_title(title: str) -> tuple[str, str]:
    """Return (status, reason) from an RSS title.

    Entity names are deliberately not used as exclusion rules. The same artist or
    series may be relevant for a major event and irrelevant for a routine article.
    """
    title = title.strip()
    if REPORT.search(title):
        return EXCLUDE, "開催後のレポート・振り返り記事のため"
    if GAME.search(title):
        return EXCLUDE, "ゲーム・eスポーツ関連で、推薦対象外のため"
    if YOUTH_STAGE.search(title):
        return EXCLUDE, "コアファン向けの2.5次元・若者向け舞台のため"
    if MATSURI_MAP.search(title) and not SCIENCE.search(title):
        return EXCLUDE, "地域の花火・祭りの網羅は別アプリで扱うため"
    if FAN_EVENT.search(title):
        return EXCLUDE, "コアなファン向けのイベント告知のため"
    if ANIME_ANNOUNCEMENT.search(title):
        return EXCLUDE, "アニメの通常の新作・放送告知で、イベント情報としての独自性が低いため"
    if ORDINARY_LIVE.search(title) and ESTABLISHED_MUSIC.search(title):
        return REVIEW, "知名度が高いアーティスト。公演の特別性と関東開催を確認するため"
    if ORDINARY_LIVE.search(title) and not MAJOR.search(title):
        return EXCLUDE, "通常のライブ・ツアー告知で、推薦基準の主要イベントに該当しないため"
    if OUTSIDE_LOCATION.search(title) and not REMOTE.search(title) and not TARGET_LOCATION.search(title):
        return EXCLUDE, "対象地域外の開催を示唆し、関東開催・全国視聴の手がかりがないため"
    if SCIENCE.search(title):
        return REVIEW, "天文・科学の注目候補。日本での観測条件と日時を確認するため"
    if SPORTS.search(title):
        return REVIEW, "スポーツの注目候補。試合日程と国内の視聴方法を確認するため"
    if TV.search(title):
        return REVIEW, "番組・配信の注目候補。初回日時と日本での視聴方法を確認するため"
    if MAJOR.search(title):
        return RECOMMEND, "主要イベントまたは幅広い関心が見込める題材を含むため"
    if EVENT.search(title):
        return REVIEW, "イベントの可能性はあるが、知名度・開催条件の追加確認が必要なため"
    return EXCLUDE, "イベント開催を示す情報が不足しているため"
