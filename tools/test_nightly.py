import os
import sys
import unittest
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nightly import choose_feed, should_publish  # noqa: E402


def utc(*a):
    return datetime(*a, tzinfo=timezone.utc)


class ChooseFeedTest(unittest.TestCase):
    def test_fresh_ten_days_feed_wins(self):
        self.assertEqual(choose_feed(utc(2026, 10, 25, 0, 44), utc(2026, 10, 25, 2, 30)), 'Gtfs_10_days.zip')

    def test_stale_ten_days_feed_falls_back_to_main(self):
        self.assertEqual(choose_feed(utc(2026, 10, 21, 0, 44), utc(2026, 10, 25, 2, 30)), 'israel-public-transportation.zip')

    def test_missing_ten_days_feed_falls_back_to_main(self):
        self.assertEqual(choose_feed(None, utc(2026, 10, 25, 2, 30)), 'israel-public-transportation.zip')


class ShouldPublishTest(unittest.TestCase):
    live = {'feed': 'israel-public-transportation.zip', 'feedModified': '2026-10-24T16:55:15+00:00',
            'lastDate': '2026-11-07'}

    def test_unchanged_source_with_enough_days_is_skipped(self):
        self.assertFalse(should_publish(self.live, 'israel-public-transportation.zip',
                                        '2026-10-24T16:55:15+00:00', date(2026, 10, 26)))

    def test_new_source_file_is_published(self):
        self.assertTrue(should_publish(self.live, 'israel-public-transportation.zip',
                                       '2026-10-25T16:55:15+00:00', date(2026, 10, 26)))

    def test_switching_feed_is_published(self):
        self.assertTrue(should_publish(self.live, 'Gtfs_10_days.zip',
                                       '2026-10-24T16:55:15+00:00', date(2026, 10, 26)))

    def test_less_than_a_week_left_is_published(self):
        self.assertTrue(should_publish(self.live, 'israel-public-transportation.zip',
                                       '2026-10-24T16:55:15+00:00', date(2026, 11, 1)))

    def test_nothing_published_yet(self):
        self.assertTrue(should_publish(None, 'Gtfs_10_days.zip', None, date(2026, 10, 26)))


if __name__ == '__main__':
    unittest.main()
