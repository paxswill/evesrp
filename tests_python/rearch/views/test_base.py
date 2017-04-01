import datetime as dt
try:
    from unittest import mock
except ImportError:
    import mock

import flask
import pytest

from evesrp import new_models as models
from evesrp import new_views as views
from evesrp import storage
from evesrp.__version__ import __version__


@pytest.fixture
def flask_app(flask_app, monkeypatch):
    monkeypatch.setattr('evesrp.__version__.__version__', '0.0.0')
    flask_app.config['SRP_SITE_NAME'] = u'EVE-SRP Testing'
    flask_app.register_blueprint(views.base.blueprint)
    return flask_app


@pytest.mark.parametrize('permission_type', (
    models.PermissionType.review,
    models.PermissionType.pay,
    models.PermissionType.submit,
    models.PermissionType.audit,
), ids=lambda p: p.name)
def test_request_count(flask_app, store, monkeypatch, permission_type):
    counts = {
        models.PermissionType.review: 1,
        models.PermissionType.pay: 2,
        models.PermissionType.submit: 3,
        # This is a dummy value, and shouldn't be actually exposed by
        # request_count
        models.PermissionType.audit: 9,
    }
    # Mock it up
    store.filter_sparse.return_value = list(range(counts[permission_type]))
    mock_user = mock.Mock()
    mock_user.user.id_ = 2
    mock_user.get_permissions.return_value = [
        models.Permission(10, 1, models.PermissionType.review),
        models.Permission(10, 1, models.PermissionType.pay),
        models.Permission(10, 1, models.PermissionType.submit),
    ]
    monkeypatch.setattr('flask_login.current_user', mock_user)
    # Actual testing
    with flask_app.app_context():
        template_count = flask.render_template_string(
            u"{{ request_count(permission_type) }}",
            permission_type=permission_type)
        function_count = views.base.request_count(permission_type)
    assert int(template_count) == function_count
    if permission_type == models.PermissionType.audit:
        assert function_count == 0
    else:
        assert function_count == counts[permission_type]


@pytest.mark.parametrize('template,expected', (
    (u"{{ app_version }}", __version__),
    (u"{{ site_name }}", u"EVE-SRP Testing"),
    (u"{{ ActionType.evaluating.name }}", u"evaluating"),
    (u"{{ PermissionType.audit.name }}", u"audit"),
    (u"{{ ModifierType.absolute.name }}", u"absolute"),
    # This is punting testing the actual operation of versioned_static to
    # another test.
    (u"{{ 'yes' if static_file is not none else 'no' }}", u"yes"),
), ids=('app_version', 'site_name', 'actiontype', 'permissiontype',
        'modifiertype', 'versioned_static'))
def test_template_globals(flask_app, template, expected):
    with flask_app.app_context():
        assert flask.render_template_string(template) == expected
