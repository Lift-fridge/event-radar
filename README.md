# EVENT RADAR automatic news discovery (v0.2)

- GitHub Actions: scheduled daily at 00:17 UTC (09:17 JST), plus manual workflow_dispatch.
- Collects RSS titles, article URLs and publication timestamps from SPICE, 音楽ナタリー, 映画ナタリー, マイナビニュース. No paid API or external Python dependencies.
- `data/discovery.json` contains **unverified news leads**, **not confirmed events**. Article publication dates must never be used as event dates. No entries are promoted to the published event list automatically.
- Missing dates/time, BS-only availability and Japanese viewability require verification. Titles are preliminary keyword leads, and can include false positives or miss relevant events.
- Feed failures are logged without writing a misleading empty success if all sources fail. Metadata retained for up to 14 days based on published timestamp, limited to 60 entries.
- Public repository publishes only feed-supplied article metadata; do not ingest full article bodies. Check each provider's terms before production redistribution or monetization.
- GitHub Pages may **not redeploy from a GITHUB_TOKEN push** when using a branch deployment. Verify Pages rebuild after the scheduled run; if it does not, change Pages Source to GitHub Actions and use an explicit deployment workflow. Until then new JSON may be in the repository but not visible in the deployed app.
- Scheduled GitHub Actions can be delayed or disabled after repository inactivity; usage and free-plan limits are subject to GitHub terms.
- Run locally: `python3 scripts/collect_news.py`. For the first run, open Actions > Refresh EVENT RADAR news leads > Run workflow. Check workflow logs and Pages URL.

## Event verification queue (proposed v0.3)

On each RSS refresh, `scripts/build_review_queue.py` writes `data/review_queue.json` using the news-lead metadata. Every row is **unverified and not publishable**. It records classification, preliminary location hint, article URL, and mandatory verification checks. It does **not** scrape full articles or infer an event date from the article timestamp.

- For in-person events, prioritize Tokyo, Kanagawa, Chiba, and Saitama. Other locations may qualify only when the event can be meaningfully watched remotely in Japan or has exceptional national importance (requires editorial verification).
- Do not infer an event's venue from a location appearing in an article headline. A city name might refer to a tour stop, publisher, or unrelated context.
- Verify event start/end date, time, venue, participation/viewing availability, whether TV is exclusively BS, official page, ticket deadlines, and reasons to feature. Store evidence before publishing anything.
- Routine local fireworks and neighborhood festivals are not the focus of EVENT RADAR; map-based coverage is planned for a separate future app. Exceptional flagship festivals may still be considered.
- The workflow runs the focused unit-test suite before updating data. If collection or tests fail, it will not publish the new generated JSON.
- This stage does **not** add automatic official-site verification, approval UI, or automatic publication. It is a review preparation layer only. 

## STEP 1: candidate-quality improvements (proposed)

- Candidate selection now treats gaming/e-sports and narrow 2.5-dimensional youth-stage events as outside EVENT RADAR's focus, and removes after-event reports and ordinary local fireworks/matsuri updates. The latter can be handled by a separate future map app.
- For physical attendance, Tokyo, Kanagawa, Chiba and Saitama are preferred. Obvious titles referring only to out-of-area events are excluded at the **headline candidate** stage unless remote viewing or a Kanto stop is mentioned. Unknown venue must still be verified, and headline rules may miss or incorrectly exclude cross-region tours.
- For music, special attention is given to established or widely mainstream performers; a name match only produces **要確認**, not a confirmed event or automatic publication. Generic smaller live announcements are suppressed.
- Added provisional RSS feeds: AstroArts (astronomical events), Yahoo! Sports (sports), Yahoo! Entertainment and AV Watch (TV/film), NHK Science/Culture. Existing sources remain. RSS URL support, reliability and redistribution conditions must be monitored; failures are visible in `data/discovery.json.errors` and do not stop successful feeds.
- Titles mentioning astronomy, major sports and television premieres can now become review leads even without the usual event verbs. News article publication timestamp must **never** be treated as the event date.
- Round-robin source selection reduces a single fast-moving news outlet monopolizing the 60-candidate cap. This is a diversity heuristic, not comprehensive event coverage.
- This phase does **not** verify official event schedules, Japanese streaming rights or location and does not auto-publish event cards.
