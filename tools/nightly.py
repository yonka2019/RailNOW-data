"""Nightly timetable build: pick the freshest MOT feed, extract trains, write the files the app downloads.

Usage: python -I tools/nightly.py <out_dir>
Writes <out_dir>/rail.json.gz and <out_dir>/meta.json.
"""
import gzip
import json
import os
import shutil
import sys
import tempfile
import urllib.request
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_rail import extract  # noqa: E402

BASE = 'https://gtfs.mot.gov.il/gtfsfiles/'
TEN_DAYS = 'Gtfs_10_days.zip'   # has real wait times, but MOT does not always refresh it
MAIN = 'israel-public-transportation.zip'   # refreshed nightly, arrival == departure
MAX_AGE = timedelta(days=2)
LIVE_META = 'https://yonka2019.github.io/RailNOW-data/meta.json'
MIN_DAYS_LEFT = 7


def choose_feed(ten_days_modified, now):
    """The 10-days feed while it is fresh (it carries wait times), else the main feed."""
    if ten_days_modified and now - ten_days_modified <= MAX_AGE:
        return TEN_DAYS
    return MAIN


def should_publish(live, feed, feed_modified, today):
    """Publish only real news: another feed, a newer source file, or under a week of data left live."""
    if not live:
        return True
    if live.get('feed') != feed or live.get('feedModified') != feed_modified:
        return True
    return date.fromisoformat(live['lastDate']) < today + timedelta(days=MIN_DAYS_LEFT)


def live_meta():
    try:
        with urllib.request.urlopen(LIVE_META, timeout=60) as r:
            return json.load(r)
    except (OSError, ValueError) as e:
        print(f'live meta.json: {e}')
        return None


def set_output(publish):
    # Tells the workflow whether to run the publish steps.
    path = os.environ.get('GITHUB_OUTPUT')
    if path:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(f"publish={'true' if publish else 'false'}\n")


def last_modified(name):
    # A 1-byte range request returns the headers without downloading the whole zip.
    req = urllib.request.Request(BASE + name, headers={'Range': 'bytes=0-0'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            value = r.headers.get('Last-Modified')
            return parsedate_to_datetime(value) if value else None
    except OSError as e:
        print(f'{name}: {e}')
        return None


def main(out_dir):
    now = datetime.now(timezone.utc)
    ten_modified = last_modified(TEN_DAYS)
    feed = choose_feed(ten_modified, now)
    modified = ten_modified if feed == TEN_DAYS else last_modified(MAIN)
    modified_iso = modified.isoformat() if modified else None
    print(f'feed: {feed} (modified {modified})')
    # The runner has a tz database; loaded here so tests run on machines without one.
    today = now.astimezone(ZoneInfo('Asia/Jerusalem')).date()

    force = os.environ.get('FORCE') == 'true'
    if not force and not should_publish(live_meta(), feed, modified_iso, today):
        print('source unchanged and enough days left: nothing to publish')
        set_output(False)
        return

    with tempfile.TemporaryDirectory() as tmp:
        zip_path = os.path.join(tmp, feed)
        with urllib.request.urlopen(BASE + feed, timeout=600) as r, open(zip_path, 'wb') as f:
            shutil.copyfileobj(r, f, 1 << 20)
        data = extract(zip_path, start=today, days=14)

    os.makedirs(out_dir, exist_ok=True)
    with gzip.open(os.path.join(out_dir, 'rail.json.gz'), 'wt', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    meta = {
        'generated': now.isoformat(timespec='seconds'),
        'feed': feed,
        'feedModified': modified_iso,
        'firstDate': data['firstDate'],
        'lastDate': data['lastDate'],
        'waits': data['waits'],
        'trips': len(data['trips']),
    }
    with open(os.path.join(out_dir, 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print(json.dumps(meta, ensure_ascii=False))
    set_output(True)


if __name__ == '__main__':
    main(sys.argv[1])
