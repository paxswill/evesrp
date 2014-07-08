from datetime import tzinfo, timedelta


class UTC(tzinfo):

    def utcoffset(self, dt):
        return timedelta()

    def dst(self, dt):
        return timedelta()

    def tzname(self, dt):
        return u'UTC+00:00'


utc = UTC()
