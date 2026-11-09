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
