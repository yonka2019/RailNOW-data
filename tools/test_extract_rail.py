import io
import os
import sys
import unittest
import zipfile
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_rail import extract  # noqa: E402


def write_zip(path, files):
    with zipfile.ZipFile(path, 'w') as z:
        for name, text in files.items():
            z.writestr(name, text.encode('utf-8'))


def make_zip(path):
    """The 10-days feed's shape: one service per date in calendar_dates.txt, padded departure times."""
    write_zip(path, {
        'agency.txt': 'agency_id,agency_name\n2,רכבת ישראל\n3,אגד\n',
        'routes.txt': 'route_id,agency_id,route_short_name,route_long_name\nR1,2,,נהריה - מודיעין\nB1,3,1,אוטובוס\n',
        'calendar_dates.txt': 'service_id,date,exception_type\n20261022,20261022,1\n',
        'trips.txt': 'route_id,service_id,trip_id,trip_headsign\nR1,20261022,T1,131\nB1,20261022,X1,bus\n',
        'stops.txt': ('stop_id,stop_code,stop_name,stop_desc,stop_lat,stop_lon\n'
                      '10,1,נהריה,,33.0,35.1\n11,2,קרית מוצקין,,32.83,35.07\n12,3,תל אביב מרכז,,32.08,34.79\n'
                      '99,9,תחנת אוטובוס,,32.0,34.0\n'),
        'stop_times.txt': ('trip_id,arrival_time,departure_time,stop_id,stop_sequence,pickup_type,drop_off_type\n'
                           'T1,23:00:00,23:00:00,10,1,0,1\n'
                           'T1,25:10:00,25:10:00,12,3,1,0\n'
                           'T1,24:05:00,24:06:00,11,2,0,0\n'
                           'X1,10:00:00,10:00:00,99,1,0,0\n'),
        'translations.txt': ('trans_id,lang,translation\n'
                             'נהריה,EN,Nahariyya\nנהריה,AR,نهاريا\nתחנת אוטובוס,EN,Bus stop\n'),
    })


def main_feed_zip():
    """The main feed's shape: weekday calendar.txt, no calendar_dates, arrival == departure."""
    buf = io.BytesIO()
    write_zip(buf, {
        'routes.txt': 'route_id,agency_id,route_short_name,route_long_name\nR1,2,,נהריה - מודיעין\n',
        'calendar.txt': ('service_id,sunday,monday,tuesday,wednesday,thursday,friday,saturday,start_date,end_date\n'
                         'S1,0,0,0,0,1,0,0,20261022,20261105\n'),
        'trips.txt': 'route_id,service_id,trip_id,trip_headsign\nR1,S1,1_5,131\n',
        'stops.txt': ('stop_id,stop_code,stop_name,stop_desc,stop_lat,stop_lon\n'
                      '41293,17117,קרית מוצקין,,32.83,35.07\n37358,17038,תל אביב מרכז,,32.08,34.79\n'),
        'stop_times.txt': ('trip_id,arrival_time,departure_time,stop_id,stop_sequence,pickup_type,drop_off_type\n'
                           '1_5,20:05:00,20:05:00,41293,1,0,1\n1_5,21:33:00,21:33:00,37358,2,1,0\n'),
    })
    buf.seek(0)
    return buf


def savidor_zip(arrival, departure):
    """Motzkin -> Savidor -> airport; Savidor in the middle, where riders board."""
    buf = io.BytesIO()
    write_zip(buf, {
        'routes.txt': 'route_id,agency_id,route_short_name,route_long_name\nR1,2,,נהריה - מודיעין\n',
        'calendar_dates.txt': 'service_id,date,exception_type\nS1,20261022,1\n',
        'trips.txt': 'route_id,service_id,trip_id,trip_headsign\nR1,S1,T1,174\n',
        'stops.txt': ('stop_id,stop_code,stop_name,stop_desc,stop_lat,stop_lon\n'
                      '1,17117,קרית מוצקין,,32.83,35.07\n2,17038,תל אביב מרכז,,32.08,34.79\n'
                      '3,17090,נתב"ג,,32.0,34.87\n'),
        'stop_times.txt': ('trip_id,arrival_time,departure_time,stop_id,stop_sequence,pickup_type,drop_off_type\n'
                           'T1,17:28:00,17:30:00,1,1,0,1\n'
                           f'T1,{arrival},{departure},2,2,0,0\n'
                           'T1,19:15:00,19:15:00,3,3,1,0\n'),
    })
    buf.seek(0)
    return buf


def savidor_stop(out):
    return out['trips'][0]['stops'][1][1:3]


class ExtractTest(unittest.TestCase):
    def test_extract_builds_rail_only(self):
        buf = io.BytesIO()
        make_zip(buf)
        buf.seek(0)
        out = extract(buf)
        self.assertEqual(len(out['trips']), 1)
        trip = out['trips'][0]
        self.assertEqual(trip['train'], '131')
        self.assertEqual(trip['date'], '2026-10-22')
        self.assertEqual(trip['stops'][1][1:3], [86700, 86700])
        self.assertEqual(trip['stops'][2][1], 90600)
        self.assertEqual(trip['stops'][0][3], 2)
        self.assertEqual(trip['stops'][2][3], 1)
        self.assertEqual(out['firstDate'], '2026-10-22')
        self.assertEqual(out['lastDate'], '2026-10-22')
        self.assertEqual(len(out['stations']), 3)
        names = [s['name'] for s in out['stations']]
        self.assertEqual(names[trip['stops'][1][0]], 'קרית מוצקין')

    def test_english_names_from_translations(self):
        buf = io.BytesIO()
        make_zip(buf)
        buf.seek(0)
        en = {s['name']: s['en'] for s in extract(buf)['stations']}
        self.assertEqual(en['נהריה'], 'Nahariyya')
        self.assertEqual(en['קרית מוצקין'], '')

    def test_no_translations_file_means_no_english(self):
        out = extract(main_feed_zip(), start=date(2026, 10, 22))
        self.assertTrue(all(s['en'] == '' for s in out['stations']))

    def test_station_id_is_stop_code(self):
        # stop_id differs between the two MOT feeds; stop_code (17117 = Motzkin) is the same in both.
        out = extract(main_feed_zip(), start=date(2026, 10, 22))
        self.assertEqual(sorted(s['id'] for s in out['stations']), ['17038', '17117'])

    def test_calendar_txt_expands_weekdays_in_window(self):
        out = extract(main_feed_zip(), start=date(2026, 10, 22), days=14)
        self.assertEqual([t['date'] for t in out['trips']], ['2026-10-22', '2026-10-29'])
        self.assertEqual((out['firstDate'], out['lastDate']), ('2026-10-22', '2026-10-29'))


    def test_padding_dropped_outside_savidor(self):
        # The published time is arrival_time; MOT pads departure_time by 1-2 min at every station but Savidor.
        stops = extract(savidor_zip('18:55:00', '18:57:00'))['trips'][0]['stops']
        self.assertEqual(stops[0][1:3], [62880, 62880])

    def test_savidor_keeps_real_wait(self):
        self.assertEqual(savidor_stop(extract(savidor_zip('18:55:00', '18:58:00'))), [68100, 68280])

    def test_savidor_gets_two_minutes_when_feed_has_none(self):
        # The main feed has arrival == departure everywhere; Savidor's real wait is 2 min.
        self.assertEqual(savidor_stop(extract(savidor_zip('18:55:00', '18:55:00'))), [68100, 68220])

    def test_savidor_as_last_stop_gets_no_wait(self):
        buf = io.BytesIO()
        make_zip(buf)
        buf.seek(0)
        last = extract(buf)['trips'][0]['stops'][2]
        self.assertEqual(last[1:3], [90600, 90600])


if __name__ == '__main__':
    unittest.main()
