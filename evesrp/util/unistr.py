import six


def unistr(klass):
    def __str__(self):
        if six.PY2:
            return self.__unicode__().encode()
        else:
            return self.__unicode__()

    klass.__str__ = __str__
    return klass


def ensure_unicode(val):
    if isinstance(val, six.binary_type):
        return val.decode('utf-8')
    return val
