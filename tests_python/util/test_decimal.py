from decimal import Decimal
from unittest import TestCase
from evesrp.util.decimal import PrettyDecimal


class TestPrettyDecimal(TestCase):

    def test_integer(self):
        pd = PrettyDecimal('123')
        self.assertEqual(pd.currency(), '123.00')
        self.assertEqual(pd, Decimal('123'))

    def test_two_decimal_places(self):
        pd = PrettyDecimal('123.45')
        self.assertEqual(pd.currency(), '123.45')
        self.assertEqual(pd, Decimal('123.45'))

    def test_three_decimal_places(self):
        pd = PrettyDecimal('123.456')
        self.assertEqual(pd.currency(), '123.46')
        self.assertEqual(pd, Decimal('123.456'))

    def test_commas(self):
        pd = PrettyDecimal('12345')
        self.assertEqual(pd.currency(commas=True), '12,345.00')
        self.assertEqual(pd.currency(commas=False), '12345.00')
