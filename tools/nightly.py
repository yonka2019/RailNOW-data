"""Nightly timetable build: download the MOT feed, extract trains, write the files the app downloads.

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
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_rail import extract  # noqa: E402

BASE = 'https://gtfs.mot.gov.il/gtfsfiles/'
# Refreshed nightly. Gtfs_10_days.zip is not (and only adds padded departure times).
FEED = 'israel-public-transportation.zip'


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
    modified = last_modified(FEED)
    modified_iso = modified.isoformat() if modified else None
    print(f'feed: {FEED} (modified {modified})')
    # The runner has a tz database; loaded here so tests run on machines without one.
    today = now.astimezone(ZoneInfo('Asia/Jerusalem')).date()

    with tempfile.TemporaryDirectory() as tmp:
        zip_path = os.path.join(tmp, FEED)
        with urllib.request.urlopen(BASE + FEED, timeout=600) as r, open(zip_path, 'wb') as f:
            shutil.copyfileobj(r, f, 1 << 20)
        data = extract(zip_path, start=today, days=14)

    os.makedirs(out_dir, exist_ok=True)
    with gzip.open(os.path.join(out_dir, 'rail.json.gz'), 'wt', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    meta = {
        'generated': now.isoformat(timespec='seconds'),
        'feed': FEED,
        'feedModified': modified_iso,
        'firstDate': data['firstDate'],
        'lastDate': data['lastDate'],
        'trips': len(data['trips']),
    }
    with open(os.path.join(out_dir, 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print(json.dumps(meta, ensure_ascii=False))


if __name__ == '__main__':
    main(sys.argv[1])
