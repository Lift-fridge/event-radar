import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from build_review_queue import queue_items


class ReviewQueueFieldTests(unittest.TestCase):
    def test_pipeline_fields_are_carried_into_review_queue(self):
        item = {
            "id": "event-1", "title": "東京の特別展", "url": "https://example.test/article",
            "status": "推薦候補", "event_group_key": "group-1",
            "related_article_urls": ["https://example.test/article", "https://example.test/followup"],
            "article_count": 2, "priority": "一般", "participation_scope": "関東現地候補",
            "verification": {"status": "unverified", "event_date": None},
        }
        row = queue_items({"items": [item]})[0]
        for key in ("event_group_key", "related_article_urls", "article_count", "priority", "participation_scope", "verification"):
            self.assertEqual(row[key], item[key])
        self.assertFalse(row["publishable"])

    def test_legacy_item_gets_compatible_defaults(self):
        row = queue_items({"items": [{"id": "legacy", "title": "旧形式", "url": "https://example.test/old"}]})[0]
        self.assertIsNone(row["event_group_key"])
        self.assertEqual(row["related_article_urls"], ["https://example.test/old"])
        self.assertEqual(row["article_count"], 1)
        self.assertEqual(row["verification"]["status"], "unverified")
        self.assertFalse(row["publishable"])
