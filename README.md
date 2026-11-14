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

## Official-calendar pilot (PR #5)

**Purpose:** separate future official *event schedules* from broad RSS news headlines. The manually checked feed remains separate from a daily, unverified discovery feed.

- Curated official seed: `data/official_schedule_sources.json` (two Japan football national-team fixtures with JFA broadcast page; two meteor showers with NAOJ monthly sky calendars).
- Daily collector: `scripts/collect_official_schedules.py` fetches the JFA schedule pages for the current and next year, and the NAOJ monthly pages for the current and next month. It writes `data/official_discovery.json` with per-source errors; every item remains `publishable: false` until reviewed.
- Builder: `scripts/build_official_schedule.py`. Strict date format, full metadata, approved state, Japan viewing/observing scope, unique IDs and HTTPS official URL are required. A record is shown only if its end date is today or later, its start date is within 60 days, and the last official check is no more than 90 days old. Date is interpreted in Japan local calendar days. The workflow refreshes `data/official_schedule.json` daily; it does *not* re-validate dates against sites automatically.
- New **公式予定（試作）** tab reads the confirmed-feed JSON without changing the older demo `見つける` cards, RSS `新着候補`, or existing favorites storage.
- TV category is supported in the schema, but **no standalone TV show is included until a concrete official date/time and terrestrial or eligible stream can be verified**. A football game carried on TV is still categorized as sports.
- The contents and data sources remain subject to official schedule changes and manual reconfirmation; this trial does not yet provide an automated sports-calendar / TV-guide feed. No guarantee of coverage beyond its four reviewed examples.
- After merging, run **Refresh EVENT RADAR news leads** once to produce the verified feed, and assess on an iPhone. More official calendar connectors/parsers and editorial approval tools can be added after validating this presentation and data policy.

## Guarded calendar auto-publication experiment (PR #7)

- Official RSS headline discovery remains unverified and separate.
- The `build_official_schedule.py` builder optionally reads `data/official_discovery.json` after `collect_official_schedules.py` refreshes it in the same daily GitHub Actions job.
- Only national observatory (NAOJ) calendar rows naming a **meteor shower peak** (「〇〇流星群が極大」) can pass the automatic calendar-date approval gate. The collector's source report must show `ok`, the generation timestamp must be no more than two JST calendar days old, the official URL must be the matching NAOJ monthly page over HTTPS, the date must match the month and be within 60 days, and duplicates of manually verified dates must be suppressed.
- Planetary station (留), elongation, generic science news, unknown sources, football matches with unverified broadcasts, parse errors, stale discovery and past dates stay **off** the public schedule.
- Automatic verification establishes **the calendar date only**. It does *not* establish a precise Japanese observing peak hour, visibility, weather, or exact best viewing window. The app labels auto-checked dates distinctly and sends users to the official monthly calendar for observing guidance.
- The previously manually verified entries, favorites and news metadata remain intact. Review source terms before any redistribution or production monetization. If source check fails the app will show no newly auto-approved date rather than guess.

## Verified domestic film-release expansion

- First additional official-date examples are **three manually selected domestic theatrical releases**: Practical Magic 2 (Warner Bros, 2026-11-27), Dune Part Three (Warner Bros, 2026-12-18), and SUKIYAKI 上を向いて歩こう (Toho, 2026-12-25). All are linked to the Japanese distributor/film official pages.
- `映画` plus `国内映画公開予定` is now an allowed *verified* schedule category/scope. This is a release **date**, not an invented fixed start time or a guaranteed screening in any particular cinema. Cinema lists/tickets can change and users should consult the official source.
- The prebuilt `data/official_schedule.json` is updated alongside `data/official_schedule_sources.json` so the separate official calendar tab can display these dates after the PR is merged. The existing GitHub Actions daily schedule builder will continue to regenerate this feed and remove past release dates.
- **Not automated yet:** distributor lineup parsing, quality/major-title editorial selection, or date change detection. The next source-specific collector should generate unverified film candidates, with approval only after the date and Japan release are independently confirmed.
- TV special schedules remain a future task; the NHK program guide API requires access credentials and may not offer a month-ahead horizon.

## Official Japanese film-release daily discovery (proposed)

- New `scripts/collect_official_films.py` scans two Japanese distributors' public official schedules daily: [Toho](https://www.toho.co.jp/movie/lineup/) and [Warner Bros Japan](https://www.warnerbros.co.jp/movie/).
- Creates `data/official_film_discovery.json` as a **separate unverified candidate list**, with per-source `ok` / `empty` / `parse_error` / `fetch_error` reports.
- Only explicitly dated upcoming domestic theatrical releases within the next 90 JST calendar days are accepted as candidates. Past releases, undated announcements, home-video releases and manually approved duplicate film dates are omitted. Failed sources can retain prior nonexpired candidates by original source URL.
- **Does not auto-publish** candidate films or auto-judge their importance: distributor schedules include niche titles, franchises and re-releases. Date changes, screenings and editorial importance need verification before inclusion.
- No external dependencies; GitHub Actions triggers film metadata discovery along with the existing daily news/sports/astronomy pipeline. Existing film cards, favorites and UI are unchanged.
- The HTML structural tests use representative markup, not a guaranteed verbatim snapshot of the live sites. On the first post-merge run, inspect source reports and titles for accuracy. Do not assume a successful HTTP fetch means successful extraction.
