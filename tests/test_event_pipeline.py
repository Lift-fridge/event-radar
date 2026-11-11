import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from classify_news import EXCLUDE, RECOMMEND, REVIEW
from event_pipeline import event_group_key, group_news_items, priority_for, classify_scope


class EventPipelineTests(unittest.TestCase):
    def test_same_event_titles_group_and_keep_related_urls(self):
        items = [
            {"title": "東京フィルメックス2026の開催概要が決定", "url": "https://a.example/1", "status": RECOMMEND},
            {"title": "東京フィルメックス2026の上映作品を発表", "url": "https://b.example/2", "status": REVIEW},
        ]
        groups = group_news_items(items)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["article_count"], 2)
        self.assertEqual(groups[0]["related_article_urls"], ["https://a.example/1", "https://b.example/2"])

    def test_different_years_are_not_merged(self):
        self.assertNotEqual(event_group_key("東京フィルメックス2026の開催概要"), event_group_key("東京フィルメックス2027の開催概要"))

    def test_results_games_and_youth_stage_are_excluded(self):
        self.assertEqual(priority_for("試合結果速報"), "一般")
        item = {"title": "若手俳優出演の2.5次元舞台", "url": "https://a.example", "status": EXCLUDE}
        self.assertEqual(group_news_items([item])[0]["status"], EXCLUDE)

    def test_priority_categories_are_detected(self):
        self.assertEqual(priority_for("プロ野球の試合日程を発表"), "スポーツ試合予定")
        self.assertEqual(priority_for("新番組の初回放送が決定"), "テレビ番組初回放送")
        self.assertEqual(priority_for("2027年の皆既月食"), "天文現象")

    def test_local_and_remote_scope_are_recorded(self):
        self.assertEqual(classify_scope("東京で開催"), "関東現地候補")
        self.assertEqual(classify_scope("全国放送で配信"), "日本からの視聴方法を要確認")

    def test_verification_fields_are_unconfirmed(self):
        item = {"title": "東京で開催", "url": "https://a.example", "status": REVIEW}
        result = group_news_items([item])[0]
        self.assertEqual(result["verification"]["status"], "unverified")
        self.assertIsNone(result["verification"]["event_date"])


if __name__ == "__main__":
    unittest.main()
