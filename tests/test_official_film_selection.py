import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from select_official_films import select

TODAY = dt.date(2026, 11, 14)


def item(name="VIVANT", date="2026-12-04", importance=None):
    return {
        "name": name, "category": "映画", "date": date,
        "source_page_url": "https://www.toho.co.jp/movie/lineup/",
        "source_type": "東宝公式映画公開予定", "status": "要確認",
        "publishable": False,
        "verification": {
            "status": "unverified",
            "japan_theatrical_release_date": "official_lineup_candidate",
            "editorial_importance": importance,
        },
    }


def discovery(items):
    return {
        "generated_at": "2026-11-14T21:50:53+09:00",
        "source_reports": [{
            "source": "東宝", "url": "https://www.toho.co.jp/movie/lineup/",
            "status": "ok", "extracted_count": len(items),
        }],
        "items": items,
    }


class OfficialFilmSelectionTests(unittest.TestCase):
    def test_title_alone_is_held(self):
        result = select(discovery([item()]), {"events": []}, TODAY)
        self.assertFalse(result["items"][0]["selection"]["publishable"])
        self.assertIn("重要度の公式根拠", " ".join(result["items"][0]["selection"]["reasons"]))

    def test_explicit_major_evidence_can_be_selected(self):
        evidence = {
            "decision": "major", "basis": ["official_franchise"],
            "evidence_url": "https://www.toho.co.jp/movie/lineup/",
            "evidence_checked_on": "2026-11-14", "review_status": "approved",
        }
        result = select(discovery([item(importance=evidence)]), {"events": []}, TODAY)
        self.assertEqual(result["items"][0]["selection"]["status"], "主要作品")
        self.assertTrue(result["items"][0]["selection"]["publishable"])

    def test_editorial_registry_is_applied_without_mutating_discovery(self):
        evidence = {"items": [{"name": "VIVANT", "date": "2026-12-04",
            "editorial_importance": {"decision": "major", "basis": ["official_franchise"],
            "evidence_url": "https://www.toho.co.jp/movie/lineup/",
            "evidence_checked_on": "2026-11-14", "review_status": "approved"}}]}
        result = select(discovery([item()]), {"events": []}, TODAY, evidence=evidence)
        self.assertTrue(result["items"][0]["selection"]["publishable"])
        self.assertIsNone(item()["verification"]["editorial_importance"])

    def test_duplicate_is_held(self):
        evidence = {
            "decision": "discovery", "basis": ["official_cultural_subject"],
            "evidence_url": "https://example.jp/film",
            "evidence_checked_on": "2026-11-14", "review_status": "approved",
        }
        schedule = {"events": [{"name": "『VIVANT』公開", "date": "2026-12-04"}]}
        result = select(discovery([item(importance=evidence)]), schedule, TODAY)
        self.assertFalse(result["items"][0]["selection"]["publishable"])
        self.assertIn("重複", " ".join(result["items"][0]["selection"]["reasons"]))

    def test_stale_source_is_held(self):
        result = select(
            {**discovery([item()]), "generated_at": "2026-11-10T00:00:00+09:00"},
            {"events": []}, TODAY)
        self.assertIn("古い", " ".join(result["items"][0]["selection"]["reasons"]))

    def test_wrong_source_status_is_held(self):
        data = discovery([item()])
        data["source_reports"][0]["status"] = "fetch_error"
        result = select(data, {"events": []}, TODAY)
        self.assertIn("取得が成功", " ".join(result["items"][0]["selection"]["reasons"]))


if __name__ == "__main__":
    unittest.main()
