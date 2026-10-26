"""Extract Israel Railways trips from a MOT GTFS zip into a compact rail.json.

Reads both MOT feeds:
- Gtfs_10_days.zip: one service per date (calendar_dates.txt), real dwell times.
- israel-public-transportation.zip: weekday ranges (calendar.txt), arrival == departure.

Stations are keyed by stop_code, which is the same in both feeds (stop_id is not).

arrival_time is the time Israel Railways publishes, and the train leaves then. The 10-days
feed pads departure_time by 1-2 min everywhere; only Savidor has a real wait (≈2 min).

Usage: python -I tools/extract_rail.py <zip> <out.json> [YYYY-MM-DD start] [days]
"""
import csv
import io
import json
import sys
import zipfile
from datetime import date, datetime, timedelta

RAIL_AGENCY = '2'
SAVIDOR = '17038'
SAVIDOR_WAIT = 120
WEEKDAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']


def _rows(z, name):
    with z.open(name) as f:
        yield from csv.DictReader(io.TextIOWrapper(f, 'utf-8-sig'))


def _sec(t):
    h, m, s = map(int, t.split(':'))
    return h * 3600 + m * 60 + s


def _day(yyyymmdd):
    return datetime.strptime(yyyymmdd, '%Y%m%d').date()


def _service_dates(z, start, days):
    """service_id -> dates it runs, limited to [start, start + days) when start is given."""
    end = start + timedelta(days=days) if start else None
    names = set(z.namelist())
    dates = {}
    if 'calendar.txt' in names:
        for r in _rows(z, 'calendar.txt'):
            d, last = _day(r['start_date']), _day(r['end_date'])
            if start:
                d, last = max(d, start), min(last, end - timedelta(days=1))
            while d <= last:
                if r[WEEKDAYS[d.weekday()]] == '1':
                    dates.setdefault(r['service_id'], set()).add(d)
                d += timedelta(days=1)
    if 'calendar_dates.txt' in names:
        for r in _rows(z, 'calendar_dates.txt'):
            d = _day(r['date'])
            if start and not start <= d < end:
                continue
            if r['exception_type'] == '1':
                dates.setdefault(r['service_id'], set()).add(d)
            elif r['exception_type'] == '2':
                dates.get(r['service_id'], set()).discard(d)
    return dates


def extract(zip_file, start=None, days=14):
    z = zipfile.ZipFile(zip_file)
    routes = {r['route_id'] for r in _rows(z, 'routes.txt') if r['agency_id'] == RAIL_AGENCY}
    dates = _service_dates(z, start, days)
    trips = {t['trip_id']: t for t in _rows(z, 'trips.txt')
             if t['route_id'] in routes and dates.get(t['service_id'])}

    times = {}
    for r in _rows(z, 'stop_times.txt'):
        if r['trip_id'] in trips:
            times.setdefault(r['trip_id'], []).append(r)

    used = {r['stop_id'] for rows in times.values() for r in rows}
    stations = [s for s in _rows(z, 'stops.txt') if s['stop_id'] in used]
    stations.sort(key=lambda s: s['stop_name'])
    index = {s['stop_id']: i for i, s in enumerate(stations)}
    savidor = {s['stop_id'] for s in stations if s['stop_code'] == SAVIDOR}

    out_trips = []
    for tid, rows in times.items():
        rows.sort(key=lambda r: int(r['stop_sequence']))
        stops = []
        for r in rows:
            flags = (1 if r.get('pickup_type') == '1' else 0) | (2 if r.get('drop_off_type') == '1' else 0)
            arr = dep = _sec(r['arrival_time'])
            if r['stop_id'] in savidor and not flags & 1:
                dep = max(_sec(r['departure_time']), arr + SAVIDOR_WAIT)
            stops.append([index[r['stop_id']], arr, dep, flags])
        t = trips[tid]
        for d in dates[t['service_id']]:
            out_trips.append({'date': d.isoformat(), 'train': t['trip_headsign'], 'stops': stops})
    out_trips.sort(key=lambda t: (t['date'], t['stops'][0][2]))

    used_dates = sorted({t['date'] for t in out_trips})
    return {
        'firstDate': used_dates[0],
        'lastDate': used_dates[-1],
        'stations': [{'id': s['stop_code'], 'name': s['stop_name'],
                      'lat': float(s['stop_lat']), 'lon': float(s['stop_lon'])} for s in stations],
        'trips': out_trips,
    }


if __name__ == '__main__':
    begin = date.fromisoformat(sys.argv[3]) if len(sys.argv) > 3 else None
    span = int(sys.argv[4]) if len(sys.argv) > 4 else 14
    data = extract(sys.argv[1], begin, span)
    with open(sys.argv[2], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    print(f"{len(data['stations'])} stations, {len(data['trips'])} trips, "
          f"{data['firstDate']}..{data['lastDate']}")
