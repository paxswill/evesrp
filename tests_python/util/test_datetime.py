from __future__ import unicode_literals

import datetime as dt
from evesrp.util.datetime import utc, parse_datetime


class TestUTC(object):

    def test_offset(self):
        assert utc.utcoffset(None).total_seconds() == 0

    def test_dst(self):
        assert utc.dst(None).total_seconds() == 0

    def test_tzname(self):
        assert utc.tzname(None) == 'UTC+00:00'


class TestParseDate(object):

    def test_simple_year(self):
        start, end = parse_datetime('2015')
        assert start, dt.datetime(2015, 1, 1, 0, 0, 0, 0, utc)
        assert end == dt.datetime(2015, 12, 31, 23, 59, 59, 999999, utc)

    def test_end_year(self):
        start, end = parse_datetime('<2015')
        assert start == dt.datetime.min
        assert end == dt.datetime(2015, 12, 31, 23, 59, 59, 999999, utc)

    def test_start(self):
        start, end = parse_datetime('>2015')
        assert start ==  dt.datetime(2015, 1, 1, 0, 0, 0, 0, utc)
        assert end == dt.datetime.max

    def test_non_leap_february(self):
        start, end = parse_datetime('2015-02')
        assert start == dt.datetime(2015, 2, 1, 0, 0, 0, 0, utc)
        assert end == dt.datetime(2015, 2, 28, 23, 59, 59, 999999, utc)

    def test_leap_february(self):
        start, end = parse_datetime('2016-02')
        assert start == dt.datetime(2016, 2, 1, 0, 0, 0, 0, utc)
        assert end == dt.datetime(2016, 2, 29, 23, 59, 59, 999999, utc)

    def test_hour_range(self):
        start, end = parse_datetime('20150314T15')
        assert start == dt.datetime(2015, 3, 14, 15, 0, 0, 0, utc)
        assert end == dt.datetime(2015, 3, 14, 15, 59, 59, 999999, utc)

    def test_year_explicit_range(self):
        start, end = parse_datetime('2015_2016')
        assert start == dt.datetime(2015, 1, 1, 0, 0, 0, 0, utc)
        assert end == dt.datetime(2016, 12, 31, 23, 59, 59, 999999, utc)

    def test_month_start_day_end(self):
        start, end = parse_datetime('2014-11_20150315')
        assert start == dt.datetime(2014, 11, 1, 0, 0, 0, 0, utc)
        assert end == dt.datetime(2015, 3, 15, 23, 59, 59, 999999, utc)
