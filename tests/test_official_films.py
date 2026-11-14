import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from collect_official_films import collect, parse_toho, parse_warner, filter_events, SOURCES

TODAY = dt.date(2026, 11, 14)
TOHO_URL = SOURCES[0][1]
WARNER_URL = SOURCES[1][1]
TOHO = """
<html><section><h3>VIVANT</h3><p>2026年12月4日（金）公開</p>
<h3>映画「SUKIYAKI 上を向いて歩こう」</h3><p>2026年12月25日（金）公開</p>
<h3>公開中作品</h3><p>公開中</p>
<h3>公開日調整中</h3><p>公開日調整中</p></section></html>
"""
WARNER = """
<html><h2>劇場公開作品</h2>
<li>2026年11月27日（金）公開映画『プラクティカル・マジック／魔女たちの秘密』近日公開</li>
<li>2026年12月18日（金）公開映画『デューン 砂の惑星 PART3』近日公開</li>
<li>映画『リメイン』近日公開</li>
<p>2026年12月25日 ブルーレイ発売『別タイトル』</p></html>
"""


class OfficialFilmsTests(unittest.TestCase):
    def test_toho_upcoming_titles_and_dates(self):
        movies, valid = parse_toho(TOHO, TOHO_URL)
        self.assertTrue(valid)
        self.assertEqual([(m["name"], m["date"]) for m in movies],
                         [("VIVANT", "2026-12-04"),
                          ("映画「SUKIYAKI 上を向いて歩こう」", "2026-12-25")])

    def test_warner_only_explicit_japan_theatrical_upcoming(self):
        movies, valid = parse_warner(WARNER, WARNER_URL)
        self.assertTrue(valid)
        self.assertEqual(len(movies), 2)
        self.assertEqual({m["date"] for m in movies}, {"2026-11-27", "2026-12-18"})
        self.assertTrue(all(m["publishable"] is False for m in movies))

    def test_historical_and_undated_movies_not_added(self):
        movies, _ = parse_toho("<h3>古い映画</h3><p>2025年1月1日（水）公開</p>", TOHO_URL)
        self.assertEqual(filter_events(movies, TODAY, {}), [])

    def test_duplicate_existing_manually_verified_film(self):
        movies, _ = parse_toho(TOHO, TOHO_URL)
        filtered = filter_events(movies, TODAY, {"events": [
            {"name": "『SUKIYAKI 上を向いて歩こう』公開", "date": "2026-12-25"}]})
        self.assertEqual([m["name"] for m in filtered], ["VIVANT"])

    def test_upcoming_must_not_be_auto_published(self):
        data = collect(TODAY, fetcher=lambda u: TOHO if "toho" in u else WARNER)
        self.assertTrue(all(x["publishable"] is False for x in data["items"]))
        self.assertTrue(all(x["verification"]["status"] == "unverified" for x in data["items"]))

    def test_source_status_and_partial_failure(self):
        def fetch(u):
            if "warnerbros" in u:
                raise TimeoutError("timeout")
            return TOHO
        result = collect(TODAY, fetcher=fetch)
        self.assertEqual([r["status"] for r in result["source_reports"]],
                         ["ok", "fetch_error"])
        self.assertTrue(result["items"])

    def test_structure_change_not_assumed_empty(self):
        data = collect(TODAY, fetcher=lambda u: "<html><p>Site redesign</p></html>")
        self.assertEqual([r["status"] for r in data["source_reports"]],
                         ["parse_error", "parse_error"])

    def test_release_page_with_no_film_dates_is_empty(self):
        data = collect(TODAY, fetcher=lambda u:
            "<h3>近日公開の作品</h3><p>公開日未定</p>" if "toho" in u
            else "<h2>近日公開</h2><p>映画『作品』近日公開</p>")
        self.assertEqual([r["status"] for r in data["source_reports"]],
                         ["empty", "empty"])

    def test_at_most_90_days_and_no_outdated_screenings(self):
        html = "<h3>作品A</h3><p>2027年4月1日（木）公開</p>"
        movies, _ = parse_toho(html, TOHO_URL)
        self.assertEqual(filter_events(movies, TODAY, {}), [])

if __name__ == "__main__":
    unittest.main()
