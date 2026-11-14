import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import collect_official_schedules as collector
from collect_official_schedules import collect, jfa_events, naoj_events


JFA_HTML = """
<table><tr><th>開催日</th><th>試合名</th><th>スコア</th><th>対戦</th><th>会場</th></tr>
<tr><td>12/20(日)</td><td><a href='/match'>国際親善試合</a></td><td>-</td><td>ブラジル</td><td>東京／国立競技場</td></tr>
<tr><td>11/1(日)</td><td>過去試合</td><td>○1-0</td><td>相手</td><td>東京</td></tr>
<tr><td>12/30(水)</td><td>〖中止〗試合</td><td>-</td><td>未定</td><td>大阪</td></tr></table>
"""
NAOJ_HTML = """
<table><tr><th>日</th><th>現象</th></tr>
<tr><td>31日</td><td>22時頃、ふたご座流星群が極大（見頃は未明）</td></tr>
<tr><td>31日</td><td>月食が見られる（日本で観測可能）</td></tr>
<tr><td>5日</td><td>天文ニュースの紹介記事</td></tr></table>
"""


class OfficialDiscoveryTests(unittest.TestCase):
    def test_jfa_future_only_and_known_cancelled_excluded(self):
        events = jfa_events(JFA_HTML, "https://jfa.example/2026.html", 2026)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["date"], "2026-12-20")
        self.assertFalse(events[0]["publishable"])
        self.assertIsNone(events[0]["verification"]["broadcast_or_streaming_in_japan"])
        self.assertEqual(events[0]["official_url"], "https://jfa.example/match")

    def test_naoj_extracts_observation_candidate_only(self):
        events = naoj_events(NAOJ_HTML, "https://nao.example/2026/12.html", 2026, 12)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["date"], "2026-12-31")
        self.assertEqual(events[1]["date"], "2026-12-31")
        self.assertFalse(events[0]["publishable"])

    def test_naoj_splits_multiple_phenomena_on_one_day(self):
        document = "<table><tr><td>13日</td><td>水星が留 / おうし座北流星群が極大</td></tr></table>"
        events = naoj_events(document, "https://nao.example/2026/11.html", 2026, 11)
        self.assertEqual([event["name"] for event in events], ["水星が留", "おうし座北流星群が極大"])
        self.assertEqual({event["date"] for event in events}, {"2026-11-13"})

    def test_successful_source_with_no_candidates_is_recorded_as_empty(self):
        payload = collect(dt.date(2026, 12, 1), fetcher=lambda url: (
            JFA_HTML if "jfa" in url else "<table><tr><th>日</th><th>現象</th></tr><tr><td>1日</td><td>満月</td></tr></table>"
        ))
        naoj = [report for report in payload["source_reports"] if report["source"] == "NAOJ"]
        self.assertTrue(naoj)
        self.assertTrue(all(report["status"] == "empty" for report in naoj))
        self.assertEqual(payload["source_errors"], [])

    def test_parse_error_preserves_previous_source_items(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "official_discovery.json"
            output.write_text(json.dumps({"items": [{
                "source_type": "JFA公式試合日程", "name": "既存予定", "date": "2026-12-10"
            }]}), encoding="utf-8")
            with patch.object(collector, "OUTPUT", output), patch.object(collector, "MANUAL_SOURCE", Path(directory) / "missing.json"), \
                    patch.object(collector, "fetch_html", return_value="<html>changed</html>"):
                collector.main()
            saved = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(saved["items"][0]["name"], "既存予定")

    def test_duplicate_manual_event_is_removed(self):
        def fetch(url):
            return JFA_HTML if "jfa" in url else NAOJ_HTML
        payload = collect(dt.date(2026, 12, 1), fetcher=fetch, manual={"events": [{"name": "国際親善試合", "date": "2026-12-20"}]})
        self.assertFalse(any(item["name"] == "国際親善試合" and item["date"] == "2026-12-20" for item in payload["items"]))

    def test_duplicate_manual_event_with_different_title_is_removed(self):
        def fetch(url):
            return JFA_HTML if "jfa" in url else NAOJ_HTML
        payload = collect(
            dt.date(2026, 12, 1), fetcher=fetch,
            manual={"events": [{"name": "サッカー日本代表 vs ブラジル代表", "date": "2026-12-20"}]},
        )
        self.assertFalse(any(item["date"] == "2026-12-20" for item in payload["items"]))

    def test_source_errors_are_recorded_individually(self):
        def fetch(url):
            if "jfa" in url and url.endswith("2027.html"):
                raise TimeoutError("fixture timeout")
            return JFA_HTML if "jfa" in url else NAOJ_HTML
        payload = collect(dt.date(2026, 12, 1), fetcher=fetch)
        self.assertTrue(any(error["source"] == "JFA" for error in payload["source_errors"]))
        self.assertGreater(payload["successful_sources"], 0)

    def test_year_end_targets_next_january(self):
        seen = []
        def fetch(url):
            seen.append(url)
            return JFA_HTML if "jfa" in url else NAOJ_HTML
        collect(dt.date(2026, 12, 31), fetcher=fetch)
        self.assertTrue(any(url.endswith("/astro/sky/2027/01.html") for url in seen))

    def test_year_start_targets_current_and_next_month(self):
        seen = []
        def fetch(url):
            seen.append(url)
            return JFA_HTML if "jfa" in url else NAOJ_HTML
        collect(dt.date(2027, 1, 1), fetcher=fetch)
        self.assertTrue(any(url.endswith("/astro/sky/2027/01.html") for url in seen))
        self.assertTrue(any(url.endswith("/astro/sky/2027/02.html") for url in seen))

    def test_malformed_source_does_not_create_guessed_events(self):
        payload = collect(dt.date(2026, 12, 1), fetcher=lambda url: "<html><body>changed</body></html>")
        self.assertEqual(payload["items"], [])


if __name__ == "__main__":
    unittest.main()

