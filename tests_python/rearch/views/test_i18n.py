from decimal import Decimal
try:
    from unittest import mock
except ImportError:
    import mock
import uuid

import babel
import flask
import flask_babel
import pytest

import evesrp.i18n._blueprint as bprint


@pytest.fixture
def enabled_locales():
    return ['en_US', 'en_GB', 'es', 'nl']


@pytest.fixture
def flask_app(flask_app, enabled_locales):
    # enabled_locales can be None when overridden by specific tests
    if enabled_locales is not None:
        flask_app.config['SRP_LOCALES'] = enabled_locales
    flask_app.register_blueprint(bprint.blueprint)
    return flask_app


@pytest.mark.parametrize('requested_locale', (None, 'en_US', 'en_GB', 'kr'),
                         ids=lambda l: 'none' if l is None else l)
def test_locale_selector(monkeypatch, flask_app, requested_locale):
    session = {}
    if requested_locale is not None:
        session['locale'] = requested_locale
    monkeypatch.setattr(flask, 'session', session)
    with flask_app.app_context():
        selected_locale = bprint.locale_selector()
    if requested_locale is None or requested_locale == 'kr':
        assert selected_locale is None
        # locale_selector needs to delete the 'locale' key from the session if
        # it's invalid
        assert 'locale' not in session
    else:
        assert selected_locale == requested_locale


def test_attach_blueprint(monkeypatch):
    babel_manager = mock.Mock()
    monkeypatch.setattr(bprint, 'babel', babel_manager)
    app = flask.Flask(__name__)
    app.register_blueprint(bprint.blueprint)
    babel_manager.init_app.assert_called_once_with(app)
    assert 'i18n' in app.blueprints
    # Check that it's a record_once instead of record
    app.register_blueprint(bprint.blueprint, prefix='/i18n')
    babel_manager.init_app.assert_called_once_with(app)
    app2 = flask.Flask(__name__)
    app2.register_blueprint(bprint.blueprint)
    babel_manager.init_app.assert_called_with(app2)


@pytest.mark.parametrize('current_locale', ('en', 'fr', 'de'))
def test_currencyfmt(monkeypatch, current_locale):
    locale = babel.Locale.parse(current_locale)
    monkeypatch.setattr(flask_babel, 'get_locale',
                        mock.Mock(return_value=locale))
    positive_formatted = bprint.currencyfmt(Decimal('10000.05'))
    expected_positive = {
        'en': u'10,000.05',
        # If your editor doesn't highlight that, the string is
        # 10<unicode non-breaking space>000,05
        'fr': u'10\u00a0000,05',
        'de': u'10.000,05',
    }
    assert positive_formatted == expected_positive[current_locale]
    negative_formatted = bprint.currencyfmt(Decimal('-10000.05'))
    expected_negative = {
        'en': u'-10,000.05',
        # If your editor doesn't highlight that, the string is
        # -10<unicode non-breaking space>000,05
        'fr': u'-10\u00a0000,05',
        'de': u'-10.000,05',
    }
    assert negative_formatted == expected_negative[current_locale]


@pytest.mark.parametrize('enabled_locales', (
    None,
    ['en_US', 'en_GB', 'nl'],
    ['en'],
), ids=('none', 'all', 'english_only'))
def test_enabled_locales(monkeypatch, flask_app, enabled_locales):
    with flask_app.app_context():
        locales = set(bprint.enabled_locales())
        all_locales = set(bprint.babel.list_translations())
    if enabled_locales is None:
        assert locales == all_locales
    else:
        expected_locales = {babel.Locale.parse(l) for l in enabled_locales}
        expected_locales.intersection_update(all_locales)
        assert locales == expected_locales


def test_get_translations(flask_app):
    client = flask_app.test_client()
    rv = client.get('/static/translations/en-US.json')
    assert rv.status_code == 200
