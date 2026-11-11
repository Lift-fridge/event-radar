import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from build_review_queue import build_queue, location_hint, queue_items


class ReviewQueueTests(unittest.TestCase):
    def test_one_metropolitan_prefecture_is_only_a_hint(self):
        self.assertEqual(location_hint("東京都の特別展"), "1都3県の地名あり・要確認")

    def test_non_target_area_not_auto_rejected(self):
        rows = queue_items({"items": [{"title": "大阪府から全国配信", "id": "1", "status": "要確認"}]})
        self.assertEqual(len(rows), 1)
        self.assertIn("配信の有無", rows[0]["area_hint"])

    def test_unknown_location_kept_for_review(self):
        self.assertEqual(location_hint("来年の話題の映画祭"), "開催地不明・要確認")

    def test_excluded_removed_and_legacy_kept(self):
        rows = queue_items({"items": [
            {"id": "1", "title": "対象外", "status": "対象外"},
            {"id": "2", "title": "旧形式", "status": "未確認"},
            {"id": "3", "title": "推薦", "status": "推薦候補"},
        ]})
        self.assertEqual([x["id"] for x in rows], ["2", "3"])
        self.assertEqual(rows[0]["candidate_status"], "要確認")

    def test_unverified_never_publishable(self):
        row = build_queue({"updated_at": "2026-11-11T00:00:00Z", "items": [
            {"id": "test", "title": "大きなイベント", "status": "推薦候補",
             "article_published_at": "2026-11-10T12:00:00Z"},
        ]})["items"][0]
        self.assertFalse(row["publishable"])
        self.assertEqual(row["verification_status"], "未検証")
        self.assertIsNone(row["event_date"])
        self.assertIsNone(row["official_source_url"])
        self.assertNotEqual(row["article_published_at"], row["event_date"])


if __name__ == "__main__":
    unittest.main()
