import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from approve_calendar_dates import approved_meteor_events
from build_official_schedule import build_schedule

TODAY = dt.date(2026, 12, 20)
URL = "https://www.nao.ac.jp/astro/sky/2027/01.html"

def candidate(**extra):
    row = {
        "id": "naoj-test", "name": "しぶんぎ座流星群が極大",
        "category": "天文・自然", "date": "2027-01-04", "end": "2027-01-04",
        "source_page_url": URL, "official_url": URL,
        "source_type": "国立天文台ほしぞら情報",
        "publishable": False,
        "verification": {"status": "unverified"},
    }
    row.update(extra)
    return row

def discovery(rows=None, status="ok", generated="2026-12-20T00:00:00+09:00"):
    return {
        "generated_at": generated,
        "source_reports": [{"source": "NAOJ", "status": status, "url": URL}],
        "items": rows if rows is not None else [candidate()],
    }

class AutoApprovalTests(unittest.TestCase):
    def test_confirmed_calendar_date_is_published_with_caveat(self):
        approved = approved_meteor_events(discovery(), TODAY, [])
        self.assertEqual(len(approved), 1)
        self.assertEqual(approved[0]["editorial_status"], "auto_verified_calendar_date")
        self.assertIn("見頃", approved[0]["time"])
        self.assertIn("天候", approved[0]["access"])

    def test_unverified_source_or_stale_read_is_not_published(self):
        for inp in (discovery(status="fetch_error"), discovery(status="parse_error"),
                    discovery(generated="2026-12-16T00:00:00+09:00")):
            with self.subTest(inp=inp):
                self.assertEqual(approved_meteor_events(inp, TODAY, []), [])

    def test_weak_astronomy_and_games_not_published(self):
        for title in ("土星が留", "金星の西方最大離角", "流星群イベントのゲーム"):
            with self.subTest(title=title):
                self.assertEqual(approved_meteor_events(discovery([candidate(name=title)]), TODAY, []), [])

    def test_host_url_month_and_future_dates_must_match(self):
        cases = [
            {"source_page_url": "https://fake.nao.ac.jp/astro/sky/2027/01.html",
             "official_url": "https://fake.nao.ac.jp/astro/sky/2027/01.html"},
            {"date": "2026-12-19", "end": "2026-12-19"},
            {"date": "2027-03-04", "end": "2027-03-04"},
            {"date": "2027-01-04", "end": "2027-01-05"},
            {"source_type": "JFA公式試合日程"},
            {"publishable": True},
        ]
        for update in cases:
            with self.subTest(update=update):
                self.assertEqual(approved_meteor_events(discovery([candidate(**update)]), TODAY, []), [])

    def test_duplicate_manual_and_duplicate_discoveries(self):
        one = candidate()
        self.assertEqual(approved_meteor_events(discovery([one, one]), TODAY, []).__len__(), 1)
        existing = [{"name": one["name"], "date": one["date"]}]
        self.assertEqual(approved_meteor_events(discovery(), TODAY, existing), [])

    def test_build_schedule_integrates_only_valid_candidates(self):
        result = build_schedule({"events": []}, today=TODAY,
                                discovery=discovery([candidate(), candidate(name="木星が留")]))
        self.assertEqual([x["name"] for x in result["events"]], ["しぶんぎ座流星群が極大"])

    def test_no_discovery_does_not_break_manual_schedule(self):
        self.assertEqual(build_schedule({"events": []}, today=TODAY)["events"], [])

if __name__ == "__main__":
    unittest.main()
