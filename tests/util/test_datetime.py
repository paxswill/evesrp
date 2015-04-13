from __future__ import unicode_literals

import datetime as dt
from unittest import TestCase
from evesrp.util.datetime import utc, parse_datetime


class TestUTC(TestCase):

    def test_offset(self):
        self.assertEqual(utc.utcoffset(None).total_seconds(), 0)

    def test_dst(self):
        self.assertEqual(utc.dst(None).total_seconds(), 0)

    def test_tzname(self):
        self.assertEqual(utc.tzname(None), 'UTC+00:00')


class TestParseDate(TestCase):

    def test_simple_year(self):
        start, end = parse_datetime('2015')
        self.assertEqual(start, dt.datetime(2015, 1, 1, 0, 0, 0, 0, utc))
        self.assertEqual(end, dt.datetime(2015, 12, 31, 23, 59, 59, 999999,
            utc))

    def test_end_year(self):
        start, end = parse_datetime('<2015')
        self.assertEqual(start, dt.datetime.min)
        self.assertEqual(end, dt.datetime(2015, 12, 31, 23, 59, 59, 999999,
            utc))

    def test_start(self):
        start, end = parse_datetime('>2015')
        self.assertEqual(start, dt.datetime(2015, 1, 1, 0, 0, 0, 0, utc))
        self.assertEqual(end, dt.datetime.max)

    def test_non_leap_february(self):
        start, end = parse_datetime('2015-02')
        self.assertEqual(start, dt.datetime(2015, 2, 1, 0, 0, 0, 0, utc))
        self.assertEqual(end, dt.datetime(2015, 2, 28, 23, 59, 59, 999999, utc))

    def test_leap_february(self):
        start, end = parse_datetime('2016-02')
        self.assertEqual(start, dt.datetime(2016, 2, 1, 0, 0, 0, 0, utc))
        self.assertEqual(end, dt.datetime(2016, 2, 29, 23, 59, 59, 999999, utc))

    def test_hour_range(self):
        start, end = parse_datetime('20150314T15')
        self.assertEqual(start, dt.datetime(2015, 3, 14, 15, 0, 0, 0, utc))
        self.assertEqual(end, dt.datetime(2015, 3, 14, 15, 59, 59, 999999, utc))

    def test_year_explicit_range(self):
        start, end = parse_datetime('2015_2016')
        self.assertEqual(start, dt.datetime(2015, 1, 1, 0, 0, 0, 0, utc))
        self.assertEqual(end, dt.datetime(2016, 12, 31, 23, 59, 59, 999999,
            utc))

    def test_month_start_day_end(self):
        start, end = parse_datetime('2014-11_20150315')
        self.assertEqual(start, dt.datetime(2014, 11, 1, 0, 0, 0, 0, utc))
        self.assertEqual(end, dt.datetime(2015, 3, 15, 23, 59, 59, 999999, utc))
