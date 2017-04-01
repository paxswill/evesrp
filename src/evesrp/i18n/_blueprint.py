from babel import negotiate_locale, numbers
import flask
import flask_babel
import six


if six.PY3:
    unicode = str


babel = flask_babel.Babel()


@babel.localeselector
def locale_selector():
    """Figures out which locale for the app to use from that selected by the
    user.

    If the user has selected a locale that is not allowed (meaning those that
    are configured in the config key `SRP_LOCALES`), the default locale is
    used (`en_US`). This function works together with
    :py:func:`detect_language`.
    
    :rtype: :py:class:`~babel.core.Locale` or None
    """
    requested_locale = flask.session.get('locale')
    supported_locales = [unicode(l) for l in enabled_locales()]
    if requested_locale is not None and \
            requested_locale not in supported_locales:
        requested_locale = None
        del flask.session['locale']
    return requested_locale


blueprint = flask.Blueprint('i18n',
                            'evesrp.i18n',
                            static_folder='static',
                            static_url_path='/static/translations')
blueprint.add_app_template_global(flask_babel.get_locale, 'get_locale')


@blueprint.record_once
def attach_babel(state):
    babel.init_app(state.app)


@blueprint.before_app_request
def detect_language():
    """Detects when the language is being set by the user.

    When a query argument `lang` is set, the value is compared against
    supported locales to find one that satisfies the request. Note that this
    function only checks that the app technically supports the locale, not that
    the app is configured to support it. App support is principally determined
    by if there are string translation files available when the app is
    packaged.
    
    The Babel subsytem is then signaled to refresh itself, eventually calling
    :py:func:`locale_selector`.
    """
    if 'lang' in flask.request.args:
        requested_locale = flask.request.args['lang']
        locales = [unicode(l) for l in babel.list_translations()]
        locale = negotiate_locale([requested_locale,], locales)
        flask.session['locale'] = locale
        flask_babel.refresh()


# The docs say no name is fine, it'll just use the function name. Tests say
# otherwise
@blueprint.app_template_filter('currencyfmt')
def currencyfmt(currency):
    """Format a decimal number as EVE Online ISK.

    This format is basically the same as standard USD format, but we're using
    :py:func:`babel.numbers.format_decimal` because ISK (as we're using it) is
    a fictional currency.

    :param currency: The number to format
    :rtype: str
    """
    # We're only formatting ISK, so it has a bit of a special format
    number = numbers.format_decimal(currency, format="#,##0.00;-#",
            locale=flask_babel.get_locale())
    return number


@blueprint.app_template_global('locales')
def enabled_locales():
    """Get an iterator of :py:class:`~babel.core.Locale` instances enabled for
    the app.

    If the configuration key `SRP_LOCALES` is set, this function returns the
    intersection of those locales with those that are supported by the app. If
    that key is not set, all supported locales are returned.

    :returns: iterator of :py:class:`~babel.core.Locale`s
    """
    all_locales = {unicode(l): l for l in babel.list_translations()}
    app_locales = flask.current_app.config.get('SRP_LOCALES',
                                               set(all_locales.keys()))
    for locale_str, locale in six.iteritems(all_locales):
        if locale_str in app_locales:
            yield locale
