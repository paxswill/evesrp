from babel import numbers
from flask.ext.babel import format_datetime, get_locale


def currencyfmt(currency):
    # We're only formatting ISK, so it has a bit of a special format
    number = numbers.format_decimal(currency, format="#,##0.00;-#",
            locale=get_locale())
    return number


def numberfmt(number):
    return numbers.format_number(number, locale=get_locale())


def percentfmt(percent):
    return numbers.format_percent(percent, locale=get_locale())
