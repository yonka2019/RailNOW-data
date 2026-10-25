# RailNOW-data

Nightly Israel Railways timetable for the RailNOW Android app.

- Job: `.github/workflows/timetable.yml` (04:30 IL, also "Run workflow"; tick *force* to republish)
- Publishes only when: other feed, newer source file, or < 7 days of data left live
- Source: MOT GTFS, https://gtfs.mot.gov.il/gtfsfiles/
  - `Gtfs_10_days.zip` while ≤ 2 days old (has wait times), else `israel-public-transportation.zip`
- Output (GitHub Pages, branch `gh-pages`):
  - https://yonka2019.github.io/RailNOW-data/rail.json.gz: trains, 14 days
  - https://yonka2019.github.io/RailNOW-data/meta.json: build time, feed, dates
  - https://yonka2019.github.io/RailNOW-data/privacy.html: app privacy policy

Local run: `python -I tools/nightly.py out`
Tests: `python -I tools/test_extract_rail.py && python -I tools/test_nightly.py`
