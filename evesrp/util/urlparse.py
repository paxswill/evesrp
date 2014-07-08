import six
from six.moves.urllib import parse

class UnicodeParseResult(parse.ParseResult):

    @staticmethod
    def ensure_unicode(value):
        if isinstance(value, six.binary_type):
            value = value.decode()
        return value

    def __getattr__(self, attr):
        value = super(UnicodeParseResult, self).__getattr__(attr)
        return self.ensure_unicode(value)

    def __getitem__(self, key):
        value = super(UnicodeParseResult, self).__getitem__(key)
        return self.ensure_unicode(value)


def urlparse(*args, **kwargs):
    real_parse = parse.urlparse(*args, **kwargs)
    return UnicodeParseResult(*real_parse)

urlunparse = parse.urlunparse
