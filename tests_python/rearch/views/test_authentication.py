try:
    from unittest import mock
except ImportError:
    import mock
import uuid

import flask
import flask_login
import pytest
from werkzeug.exceptions import HTTPException
import wtforms

from evesrp import new_views as views
from evesrp import new_auth as authn
from evesrp import new_models as models
from evesrp import util, storage
import evesrp.new_views.authentication._blueprint as bprint


@pytest.fixture
def flask_app(flask_app):
    flask_app.config['SRP_AUTH_METHODS'] = [
        {
            'type': 'evesrp.new_auth.evesso.EveSsoProvider',
            'client_id': mock.sentinel.client_id,
            'client_secret': mock.sentinel.client_secret,
        },

    ]
    flask_app.register_blueprint(views.authn.blueprint)
    return flask_app


def test_attach_blueprint(monkeypatch):
    login_manager = mock.Mock()
    monkeypatch.setattr(bprint, 'login_manager', login_manager)
    app = flask.Flask(__name__)
    app.register_blueprint(bprint.blueprint)
    login_manager.init_app.assert_called_once_with(app)
    assert 'authn' in app.blueprints
    # Check that login_manager is only set up once per app
    app.register_blueprint(bprint.blueprint, prefix='/authn')
    login_manager.init_app.assert_called_once_with(app)
    app2 = flask.Flask(__name__)
    app2.register_blueprint(bprint.blueprint)
    login_manager.init_app.assert_called_with(app2)


@pytest.mark.parametrize('bad_id,not_found', (
    (True, None),
    (False, True),
    (False, False),
), ids=('bad_id', 'not_found', 'found'))
def test_login_loader(flask_app, store, bad_id, not_found):
    with flask_app.app_context():
        if bad_id:
            login_user = bprint.login_loader('foo')
            assert login_user is None
        else:
            if not_found:
                store.get_user.side_effect = storage.NotFoundError('user', 123)
                login_user = bprint.login_loader(123)
                assert login_user is None
            else:
                store.get_user.return_value = mock.sentinel.user
                login_user = bprint.login_loader(123)
                assert isinstance(login_user,
                                  views.authentication.user.LoginUser)
                assert login_user.user == mock.sentinel.user
            store.get_user.assert_called_once_with(123)


def test_create_providers(flask_app, store):
    providers = bprint.create_providers(flask_app)
    assert len(providers) == 1
    assert isinstance(next(iter(providers.values())),
                      authn.evesso.EveSsoProvider)
    assert isinstance(next(iter(providers.keys())), uuid.UUID)


@pytest.mark.parametrize('fields', (
    {
        u'ugly_name': authn.LoginFieldType.string,
    },
    {
        u'ugly_name': authn.LoginFieldType.password,
    },
    {
        u'submit': u'Enter',
    },
    {
        u'submit': (u'Some alt text', 'http://example.com/foo.png'),
    },
    {
        u'submit': (u'Some alt text', 'evesso.png'),
    },
))
def test_provider_form(flask_app, fields):
    provider = mock.Mock()
    provider.fields = fields
    with flask_app.app_context():
        Form = bprint.form_for_provider(provider)
    # All the testing about the submit button
    assert hasattr(Form, 'submit')
    if u'submit' in fields:
        if isinstance(fields[u'submit'], tuple):
            # We're dealing with unbound fields here
            assert Form.submit.field_class == util.ImageField
            assert Form.submit.kwargs['alt'] == u'Some alt text'
            if not fields[u'submit'][0].startswith('http'):
                assert Form.submit.kwargs['src'].startswith('http')
        else:
            assert Form.submit.field_class == wtforms.fields.SubmitField
            assert Form.submit.args[0] == u'Enter'
    else:
        assert Form.submit.args[0] == u'Log In'
    # Testing for other fields/field types
    if u'ugly_name' in fields:
        assert Form.ugly_name.args[0] == u'Ugly name'
        if fields[u'ugly_name'] == authn.LoginFieldType.string:
            assert Form.ugly_name.field_class == wtforms.fields.StringField
        elif fields[u'ugly_name'] == authn.LoginFieldType.password:
            assert Form.ugly_name.field_class == wtforms.fields.PasswordField


@pytest.mark.parametrize('in_progress,state_match,success', (
    (False, None, None),
    (True, False, None),
    (True, True, False),
    (True, True, True),
), ids=('not_in_progress', 'state_mismatch', 'oauth_error', 'success'))
def test_second_stage(flask_app, monkeypatch, in_progress, state_match,
                      success):
    # A whole bunch of setup mocking and patching out the thread-local flask
    # stuff and global flask functions.
    session = {}
    if in_progress:
        session['provider_in_progress'] = 'foo'
    if state_match:
        session['state'] = 'good_state'
    else:
        session['state'] = 'bad_state'
    monkeypatch.setattr(flask, 'session', session)
    request_mock = mock.Mock()
    values_mock = mock.Mock()
    request_mock.values = values_mock
    values_mock.get.return_value = 'good_state'
    values_mock.to_dict.return_value = {
        'sentinel': mock.sentinel.context_args,
    }
    monkeypatch.setattr(flask, 'request', request_mock)
    url_for_mock = mock.Mock()
    url_for_mock.return_value = mock.sentinel.redirect_uri
    monkeypatch.setattr(flask, 'url_for', url_for_mock)
    login_user_mock = mock.Mock()
    monkeypatch.setattr(bprint, 'login_user', login_user_mock)
    # Create some providers
    providers = {
        'foo': mock.Mock(),
        'bar': mock.Mock(),
        'baz': mock.Mock(),
    }
    response = {}
    if success:
        response['action'] = 'success'
        response['context'] = mock.sentinel.context
    else:
        response['action'] = 'error'
    providers['foo'].create_context.return_value = response
    # Actual testing
    if not in_progress:
        assert not bprint.check_second_stage(providers, flask_app)
    else:
        if not state_match:
            with pytest.raises(HTTPException) as exc:
                bprint.check_second_stage(providers, flask_app)
            assert exc.value.code == 400
        else:
            if success:
                bprint.check_second_stage(providers, flask_app)
                login_user_mock.assert_called_once_with(providers['foo'],
                                                        mock.sentinel.context,
                                                        flask_app)
            else:
                with pytest.raises(HTTPException) as exc:
                    bprint.check_second_stage(providers, flask_app)
                assert exc.value.code == 500
            context_args = providers['foo'].create_context.call_args[1]
            assert context_args['sentinel'] == mock.sentinel.context_args
            assert context_args['redirect_uri'] == mock.sentinel.redirect_uri
            # Check that only the matching provider was used
            assert providers['foo'].create_context.called
            assert not providers['bar'].create_context.called
            assert not providers['baz'].create_context.called


class TestLoginUser(object):
    """This class is to separate out overriding the store fixture."""

    @pytest.fixture
    def store(self):
        # Not using the memory_store fixture, as there's enough differences
        # that updating this to use it would be tedious.
        store = storage.MemoryStore()
        store._data['authn_users'].update({
            (
                uuid.UUID('3a80f9c8-f552-472b-9ed4-a479cb8f8521'),
                'paxswill',
            ): {
                'user_id': 9,
                'extra_data': {},
            },
            (
                uuid.UUID('3a80f9c8-f552-472b-9ed4-a479cb8f8521'),
                'sapporo',
            ): {
                'user_id': 9,
                'extra_data': {},
            },
        })
        store._data['authn_groups'].update({
            (uuid.UUID('3a80f9c8-f552-472b-9ed4-a479cb8f8521'),
             'test'): {
                'group_id': 3000,
                'extra_data': {},
            },
            (uuid.UUID('3a80f9c8-f552-472b-9ed4-a479cb8f8521'),
             'b0rt'): {
                'group_id': 4000,
                'extra_data': {},
            },
            (uuid.UUID('3a80f9c8-f552-472b-9ed4-a479cb8f8521'),
             'ukoc'): {
                'group_id': 5000,
                'extra_data': {},
            },
            (uuid.UUID('3a80f9c8-f552-472b-9ed4-a479cb8f8521'),
             'cesspit'): {
                'group_id': 6000,
                'extra_data': {},
            },
        })
        store._data['users'].update({
            9: {
                'id': 9,
                'name': u'Paxswill',
                'is_admin': False,
            },
            7: {
                'id': 7,
                'name': u'Sapporo Jones',
                'is_admin': True,
            },
        })
        store._data['groups'].update({
            3000: {
                'id': 3000,
                'name': u'TEST Alliance',
            },
            4000: {
                'id': 4000,
                'name': u'Dreddit',
            },
            5000: {
                'id': 5000,
                'name': u'UKOC',
            },
            6000: {
                'id': 6000,
                'name': u'Fiery Cesspit',
            },
        })
        store._data['group_members'].update({
            3000: {7, 9},
            4000: {9, },
            5000: {7, },
            6000: set(),
        })
        store._data['characters'].update({
            2112311608: {
                'user_id': 7,
                'id': 2112311608,
                'name': u'marssell kross',
            },
            570140137: {
                'user_id': 9,
                'id': 570140137,
                'name': u'Paxswill',
            },
            # Grabbed some names from TEST
            95044427: {
                'user_id': None,
                'id': 95044427,
                'name': u'Elissa Oriki',
            },
            95090519: {
                'user_id': 9,
                'id': 95090519,
                'name': u'Legisis Aldent',
            },
            371879632: {
                'user_id': None,
                'id': 371879632,
                'name': u'Mara Kell',
            },
            772506501: {
                'user_id': 7,
                'id': 772506501,
                'name': u'Sapporo Jones',
            },
            1124073855: {
                'user_id': 7,
                'id': 1124073855,
                'name': u'RUSROG',
            },
            1456384556: {
                'user_id': None,
                'id': 1456384556,
                'name': u'DurrHurrDurr',
            },
        })
        # In summary, there are two users, 7 (Sappo) and 9 (Paxswill), but only
        # user #9 is being used for tests
        # User #7 is in groups 3000 and 5000
        # User #9 is in groups 3000 and 4000
        # No users are in group 6000
        # User #7 has characters 2112311608, 772506501, 1124073855
        # User #9 has characters 570140137, 95090519
        # No user is set for characters 95044427, 371879632, 1456384556
        return store


    @pytest.mark.parametrize(
        'add_characters,remove_characters,add_groups,remove_groups',
        (
            (False, False, False, False),
            (True, False, True, False),
            (False, True, False, True),
            (True, True, True, True),
        ),
        ids=(
            'change_nothing',
            'add',
            'remove',
            'add_and_remove',
        )
    )
    def test_login_user(self, flask_app, store, monkeypatch, add_characters,
                        remove_characters, add_groups, remove_groups):
        provider = mock.Mock()
        authn_user = mock.Mock(user_id=9)
        provider.get_user.return_value = authn_user
        flask_login_mock = mock.Mock()
        monkeypatch.setattr(flask_login, 'login_user', flask_login_mock)
        # Set up which characters to act like we're returning
        provider_characters = [
            {
                u'id': 570140137,
                u'name': u'Gallente Citizen 570140137',
            },
        ]
        if add_characters:
            # Adding a character already in storage
            provider_characters.append({
                u'id': 772506501,
                u'name': u'Caldari Citizen 772506501',
            })
            # Adding a character not in storage already
            provider_characters.append({
                u'id': 401195232,
                u'name': u'Helothane',
            })
        if not remove_characters:
            provider_characters.append({
                u'id': 95090519,
                u'name': u'Legisis Aldent',
            })
        provider.get_characters.return_value = provider_characters
        provider_groups = [mock.Mock(group_id=3000), ]
        if add_groups:
            provider_groups.append(mock.Mock(group_id=6000))
        if not remove_groups:
            provider_groups.append(mock.Mock(group_id=4000))
        provider.get_groups.return_value = provider_groups
        # Summary of tests:
        # Both Paxswill and Sapporo Jones will have their names updated
        # if adding a character, add 401195232 and 772506501 to #9
        # if removing a character, remove 95090519 from #9
        # if adding a group, add 6000 to #9
        # if removing a group, remove 4000 from #9
        bprint.login_user(provider, mock.sentinel.context, flask_app)
        # User assertions
        provider.get_user.assert_called_once_with(mock.sentinel.context)
        # Character assertions
        provider.get_characters.assert_called_once_with(mock.sentinel.context)
        expected_character_ids = {570140137, }
        if add_characters:
            expected_character_ids.add(772506501)
            expected_character_ids.add(401195232)
        if not remove_characters:
            expected_character_ids.add(95090519)
        characters = store.get_characters(9)
        assert expected_character_ids == {c.id_ for c in characters}
        paxswill = store.get_character(570140137)
        assert paxswill.name == u'Gallente Citizen 570140137'
        if add_characters:
            sappo = store.get_character(772506501)
            assert sappo.name == u'Caldari Citizen 772506501'
        # Group assertions
        provider.get_groups.assert_called_once_with(mock.sentinel.context)
        expected_group_ids = {3000, }
        if add_groups:
            expected_group_ids.add(6000)
        if not remove_groups:
            expected_group_ids.add(4000)
        groups = store.get_groups(9)
        assert expected_group_ids == {g.id_ for g in groups}


@pytest.mark.parametrize('is_set,is_safe', (
    (False, None),
    (True, False),
    (True, True),
), ids=('not_set', 'not_safe', 'safe'))
def test_redirect_next(monkeypatch, is_set, is_safe):
    session = {}
    if is_set:
        session['next'] = mock.sentinel.next_url
    safe_redirect = mock.Mock()
    safe_redirect.return_value = is_safe
    monkeypatch.setattr(util, 'is_safe_redirect', safe_redirect)
    monkeypatch.setattr(flask, 'url_for',
                        mock.Mock(return_value=mock.sentinel.index_url))
    redirect_mock = mock.Mock()
    redirect_mock.return_value = mock.sentinel.redirect
    monkeypatch.setattr(flask, 'redirect', redirect_mock)
    redirect = bprint.redirect_next(session)
    assert redirect == mock.sentinel.redirect
    if not (is_safe and is_set):
        redirect_mock.assert_called_once_with(mock.sentinel.index_url)
    else:
        redirect_mock.assert_called_once_with(mock.sentinel.next_url)


def test_login_user(monkeypatch):
    user = mock.Mock(id_=42)
    user.foo = mock.sentinel.foo
    login_user = bprint.LoginUser(user)
    assert login_user.user == user
    assert login_user.foo == mock.sentinel.foo
    assert login_user.get_id() == u'42'
