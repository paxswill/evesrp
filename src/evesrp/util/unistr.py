"""Unicode helper functions."""


import six


def unistr(klass):
    """Class decorator that aids in model compatibility between Python 2 and 3.

    The decorated class needs to define a :py:func:`__unicode__` function (even
    for Python 3). This decorator adds a :py:func:`__str__` function to the
    class that takes :py:func:`__unicode__`\'s return value and encodes it as
    UTF-8 on Python 2 or returns it unmodified on Python 3.
    """
    def __str__(self):
        if six.PY2:
            return self.__unicode__().encode('utf-8')
        else:
            return self.__unicode__()

    klass.__str__ = __str__
    return klass


def ensure_unicode(val):
    """Ensure that a a given value is a unicode string.

    If ``val`` is a :py:data:`six.binary_type <binary type>`, assume it's UTF-8
    and decode it.
    :param val: A :py:data:`six.binary_type <binary>` or
        :py:data:`six.text_type <text>` type.
    :rtype: :py:class:`unicode` on Python 2, :py:class:`str` on Python 3
    """
    if isinstance(val, six.binary_type):
        return val.decode('utf-8')
    return val
