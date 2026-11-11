import sys
import unittest
import datetime as dt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from build_official_schedule import build_schedule

TODAY = dt.date(2026, 11, 11)

def sample(**kwargs):
    event = {
        "id": "test", "name": "Example", "category": "天文・自然",
        "date": "2026-11-18", "end": "2026-11-18",
        "time": "9:00頃", "place": "日本の夜空", "access": "肉眼で観測",
        "why": "事前に知る価値がある", "trivia": "公式日程",
        "url": "https://www.nao.ac.jp/astro/sky/2026/11.html",
        "source_type": "国立天文台", "access_scope": "日本で観測可能",
        "source_checked_on": "2026-11-11",
        "editorial_status": "manual_official_checked",
    }
    return dict(event, **kwargs)

class OfficialCalendarTests(unittest.TestCase):
    def test_valid_future_official_record(self):
        events = build_schedule({"events": [sample()]}, TODAY)["events"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["date"], "2026-11-18")

    def test_event_past_is_excluded_not_article_date(self):
        events = build_schedule({"events": [sample(date="2026-11-01", end="2026-11-01")]}, TODAY)["events"]
        self.assertEqual(events, [])

    def test_future_more_than_60_days_is_excluded(self):
        self.assertFalse(build_schedule({"events": [sample(date="2027-02-20", end="2027-02-20")]}, TODAY)["events"])

    def test_unapproved_never_appears(self):
        self.assertFalse(build_schedule({"events": [sample(editorial_status="unverified")]}, TODAY)["events"])

    def test_outside_category_and_scope_rejected(self):
        self.assertFalse(build_schedule({"events": [sample(category="ゲーム")]}, TODAY)["events"])
        self.assertFalse(build_schedule({"events": [sample(access_scope="BS限定")]}, TODAY)["events"])

    def test_duplicate_event_id_fails(self):
        with self.assertRaises(ValueError):
            build_schedule({"events": [sample(), sample()]}, TODAY)

    def test_missing_or_malformed_date_fails(self):
        with self.assertRaises(ValueError):
            build_schedule({"events": [sample(date="2026-99-99")]}, TODAY)
        with self.assertRaises(ValueError):
            build_schedule({"events": [sample(time="")]}, TODAY)

    def test_old_official_checks_are_not_published(self):
        self.assertFalse(build_schedule({"events": [sample(source_checked_on="2026-01-01")]}, TODAY)["events"])

if __name__ == "__main__":
    unittest.main()
