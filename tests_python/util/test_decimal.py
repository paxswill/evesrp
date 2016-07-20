from decimal import Decimal
from evesrp.util.decimal import PrettyDecimal


class TestPrettyDecimal(object):

    def test_integer(self):
        pd = PrettyDecimal('123')
        assert pd.currency() == '123.00'
        assert pd == Decimal('123')

    def test_two_decimal_places(self):
        pd = PrettyDecimal('123.45')
        assert pd.currency() == '123.45'
        assert pd == Decimal('123.45')

    def test_three_decimal_places(self):
        pd = PrettyDecimal('123.456')
        assert pd.currency() == '123.46'
        assert pd == Decimal('123.456')
