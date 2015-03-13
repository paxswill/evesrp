from __future__ import absolute_import

import calendar
import datetime as dt
import re
from sqlalchemy import types
import iso8601
import iso8601.iso8601 as int_iso8601


class UTC(dt.tzinfo):

    def utcoffset(self, obj):
        return dt.timedelta()

    def dst(self, obj):
        return dt.timedelta()

    def tzname(self, obj):
        return u'UTC+00:00'


utc = UTC()


class DateTime(types.TypeDecorator):

    impl = types.DateTime

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == 'mysql':
            return dt.datetime(*(value.utctimetuple()[0:6]))
        return value


def parse_datetime(date_string):
    """Parse an ISO 8601-like string into a start and end datetime.

    Parses a data and/or time string into a pair of
    :py:class:`datetime.datetime` objects representing the beginning and end
    period. A detail description of the formats accepted follows:

    The time zone is UTC, and seconds precision is not supported.
    Date ranges may be specified by two datestrings separated by an underscore.
    Dates may be written in either the basic or extended format.
    Datestrings with a leading `<` or `>` character will be parsed as a range
    starting or ending with :py:attr:`datetime.datetime.min` and
    :py:attr:`datetime.datetime.max` repsectively.

    ==============   ========================== ==========================
    String           Start Time (incl.)         End Time (incl.)
    --------------   -------------------------- --------------------------
    2015             2015-01-01T00:00           2015-01-31T23:59
    2015-02          2015-02-01T00:00           2015-02-28T23:59
    20150314         2015-03-14T00:00           2015-03-15T23:59
    20150314T15      2015-03-14T15:00           2015-03-15T15:59
    2015_2016        2015-01-01T00:00           2016-12-31T23:59
    2014-11_20150315 2014-11-01T00:00           2015-03-15T23:59
    <2015            :py:attr:`~.datetime.min`  2015-12-31T23:59
    >201408          2014-08-01T00:00           :py:attr:`~.datetime.max`
    ==============   ========================== ==========================

    :param str date_string: An ISO 8601 formatted date or date range.
    :returns: The start and end :py:class:`datetime.datetime`\s
    :rtype: tuple
    """

    def parse_start(start_string):
        return iso8601.parse_date(start_string)

    def parse_end(end_string):
        # Adapted from iso8601.parse_date, defaulting to the max instead of
        # minimum time for missing time elements.
        match = int_iso8601.ISO8601_REGEX.match(end_string)
        if match is None:
            raise iso8601.ParseError(
                    "Unable to parse date string %r" % end_string)
        groups = match.groupdict()
        year = int_iso8601.to_int(groups, 'year')
        month = int_iso8601.to_int(groups, 'month',
                default=int_iso8601.to_int(groups, 'monthdash', required=False,
                    default=dt.datetime.max.month))
        # Find the last day for the given month and year (accounting for leap
        # years).
        max_day = calendar.monthrange(year, month)[1]
        day = int_iso8601.to_int(groups, 'day',
                default=int_iso8601.to_int(groups, 'daydash', required=False,
                    default=max_day))
        hour = int_iso8601.to_int(groups, 'hour',
                default=dt.datetime.max.hour)
        minute = int_iso8601.to_int(groups, 'minute',
                default=dt.datetime.max.minute)
        second = int_iso8601.to_int(groups, 'second',
                default=dt.datetime.max.second)
        try:
            return dt.datetime(year=year, month=month, day=day, hour=hour,
                    minute=minute, second=second,
                    microsecond=dt.datetime.max.microsecond,
                    tzinfo=utc)
        # Catch ValueError, as that'd what datetime.datetime is documented to
        # raise.
        except ValueError as e:
            raise iso8601.ParseError(e)

    # Start with checking for min or max ranges
    if date_string[0] == '<':
        start_time = dt.datetime.min
        end_time = parse_end(date_string[1:])
    elif date_string[0] == '>':
        start_time = parse_start(date_string[1:])
        end_time = dt.datetime.max
    # Check for explicit ranges
    elif '_' in date_string:
        start_string, end_string = date_string.split('_', 1)
        start_time = parse_start(start_string)
        end_time = parse_end(end_string)
    # Otherwise just parse the given string as the start and end times.
    else:
        start_time = parse_start(date_string)
        end_time = parse_end(date_string)
    return start_time, end_time
