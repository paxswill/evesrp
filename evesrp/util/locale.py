import six
from babel import numbers, Locale
from flask import current_app
from flask.ext.babel import format_datetime, get_locale
from .. import babel


if six.PY3:
    unicode = str


def currencyfmt(currency):
    # We're only formatting ISK, so it has a bit of a special format
    number = numbers.format_decimal(currency, format="#,##0.00;-#",
            locale=get_locale())
    return number


def numberfmt(number):
    return numbers.format_number(number, locale=get_locale())


def percentfmt(percent):
    return numbers.format_percent(percent, locale=get_locale())


def enabled_locales():
    all_locales = [(unicode(l), l) for l in babel.list_translations()]
    enabled_locales = current_app.config.get('SRP_LOCALES', [])
    if not enabled_locales:
        for locale in all_locales:
            yield locale[0]
    else:
        for enabled_locale in enabled_locales:
            for locale_str, locale in all_locales:
                if locale_str == enabled_locale:
                    yield locale
