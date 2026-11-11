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


if __name__ == "__main__":
    unittest.main()
