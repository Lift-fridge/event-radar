import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from classify_news import EXCLUDE, RECOMMEND, REVIEW, classification_counts, classify_title, visible_items


class ClassifyNewsTests(unittest.TestCase):
    def test_live_report_is_excluded(self):
        status, reason = classify_title("柿原徹也、デビュー15周年を締めくくるライブファイナルのオフィシャルライブレポートが到着")
        self.assertEqual(status, EXCLUDE)
        self.assertIn("レポート", reason)

    def test_routine_anime_announcement_is_excluded(self):
        status, reason = classify_title("TVアニメ『みなみけ これから』ティザービジュアル、放送時期、キャスト解禁")
        self.assertEqual(status, EXCLUDE)
        self.assertIn("アニメ", reason)

    def test_ordinary_live_by_newer_artist_is_excluded_without_name_blacklist(self):
        status, _ = classify_title("優里、自身最大規模となるZeppワンマンライブを東京・大阪で開催")
        self.assertEqual(status, EXCLUDE)

    def test_major_event_is_recommended(self):
        status, _ = classify_title("第27回 東京フィルメックス映画祭の開催概要が決定")
        self.assertEqual(status, RECOMMEND)

    def test_event_without_major_signal_needs_review(self):
        status, _ = classify_title("地域文化フェアの開催が決定")
        self.assertIn(status, (RECOMMEND, REVIEW))

    def test_counts_include_each_classification(self):
        items = [{"status": RECOMMEND}, {"status": REVIEW}, {"status": EXCLUDE}, {"status": EXCLUDE}]
        self.assertEqual(classification_counts(items), {RECOMMEND: 1, REVIEW: 1, EXCLUDE: 2})

    def test_review_queue_hides_excluded_items(self):
        items = [{"title": "keep", "status": RECOMMEND}, {"title": "check", "status": REVIEW}, {"title": "hide", "status": EXCLUDE}]
        self.assertEqual([item["title"] for item in visible_items(items)], ["keep", "check"])

    def test_legacy_item_without_status_stays_visible_as_review(self):
        items = [{"title": "legacy"}, {"title": "hide", "status": EXCLUDE}]
        self.assertEqual([item["title"] for item in visible_items(items)], ["legacy"])
        self.assertEqual(classification_counts(items), {RECOMMEND: 0, REVIEW: 1, EXCLUDE: 1})

    def test_after_event_fireworks_report_not_recommended(self):
        status, _ = classify_title("第38回 なにわ淀川花火大会 大迫力ショーをレポート")
        self.assertEqual(status, EXCLUDE)

    def test_core_fan_youth_stage_excluded(self):
        status, _ = classify_title("舞台『刀剣乱舞』十周年記念公演が開幕")
        self.assertEqual(status, EXCLUDE)

    def test_gaming_event_excluded(self):
        status, _ = classify_title("eスポーツ世界大会の開催決定")
        self.assertEqual(status, EXCLUDE)

    def test_outside_kanto_exhibition_excluded(self):
        status, reason = classify_title("画家の京都展が開催決定")
        self.assertEqual(status, EXCLUDE)
        self.assertIn("地域外", reason)

    def test_kanto_and_outside_in_one_title_is_reviewed(self):
        status, _ = classify_title("東京・大阪で特別展を開催")
        self.assertNotEqual(status, EXCLUDE)

    def test_remote_tv_overseas_is_reviewed(self):
        status, _ = classify_title("大阪で開催の全国放送音楽特番が決定")
        self.assertNotEqual(status, EXCLUDE)

    def test_sky_event_stays_in_review(self):
        status, reason = classify_title("2026年11月16日 火星と木星が大接近")
        self.assertEqual(status, REVIEW)
        self.assertIn("天文", reason)

    def test_sports_and_tv_stay_reviewable(self):
        for title in ("サッカー日本代表のブラジル戦 11月14日キックオフ", "人気ドラマの初回放送日が発表"):
            with self.subTest(title=title):
                self.assertNotEqual(classify_title(title)[0], EXCLUDE)

    def test_unrelated_item_stays_excluded(self):
        status, _ = classify_title("スマートフォンの新製品を発表")
        self.assertEqual(status, EXCLUDE)


if __name__ == "__main__":
    unittest.main()
