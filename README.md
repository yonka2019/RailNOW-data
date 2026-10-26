# RailNOW-data

Nightly Israel Railways timetable for the RailNOW Android app.

- Job: `.github/workflows/timetable.yml` (04:30 IL, also "Run workflow")
- Publishes every night; the app downloads once a day (when `generated` changes)
- Source: MOT GTFS, https://gtfs.mot.gov.il/gtfsfiles/israel-public-transportation.zip (refreshed nightly)
- Times: `arrival_time` everywhere (the time Israel Railways publishes); Savidor leaves 2 min later
- Output (GitHub Pages, branch `gh-pages`):
  - https://yonka2019.github.io/RailNOW-data/rail.json.gz: trains, 14 days
  - https://yonka2019.github.io/RailNOW-data/meta.json: build time, feed, dates
  - https://yonka2019.github.io/RailNOW-data/privacy.html: app privacy policy

Local run: `python -I tools/nightly.py out`
Tests: `python -I tools/test_extract_rail.py`
