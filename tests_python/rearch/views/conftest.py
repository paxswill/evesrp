try:
    from unittest import mock
except ImportError:
    import mock

import flask
import flask_babel
import pytest

from evesrp import storage


@pytest.fixture
def store():
    store = mock.create_autospec(storage.BaseStore)
    return store


@pytest.fixture
def flask_app(store):
    app = flask.Flask('evesrp')
    app.config['TESTING'] = True
    app.config['SERVER_NAME'] = 'localhost'
    app.store = store
    babel = flask_babel.Babel(app)
    return app
