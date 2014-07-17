from __future__ import absolute_import
from decimal import Decimal
import six
from sqlalchemy.types import TypeDecorator, Numeric


if six.PY3:
    unicode = str


class PrettyDecimal(Decimal):
    """:py:class:`~.Decimal` subclass that can pretty-print itself."""

    def currency(self, commas=True):
        """Format the Decimal as a currency number.

        Commas for the thousands separators, full stops for the decimal, two
        decimal places. Commas are optional and controlled by the ``commas``
        argument.

        Adapted from https://docs.python.org/3.3/library/decimal.html#recipes
        """
        sign, digits, exp = self.quantize(Decimal('0.01')).as_tuple()
        digits = list(map(unicode, digits))
        result = []
        for i in range(2):
            result.append(digits.pop() if digits else u'0')
        result.append(u'.')
        if not digits:
            result.append(u'0')
        count = 0
        while digits:
            result.append(digits.pop())
            count += 1
            if count == 3 and digits and commas:
                count = 0
                result.append(u',')
        result.append(u'-' if sign else u'')
        return u''.join(reversed(result))


class PrettyNumeric(TypeDecorator):
    """Type Decorator for :py:class:`~.Numeric` that reformats the values into
    :py:class:`PrettyDecimal`\s.
    """

    impl = Numeric

    def process_result_value(self, value, dialect):
        return PrettyDecimal(value) if value is not None else None
