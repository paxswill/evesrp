try:
    from unittest import mock
except ImportError:
    import mock
import pytest
from evesrp import search_filter as sfilter
from evesrp import users, storage
from evesrp import new_models as models


@pytest.fixture
def browse_store():
    store = mock.create_autospec(storage.BaseStore, instance=True)
    return store


@pytest.fixture(params=(True, False), ids=('no_filter', 'with_filter'))
def add_filter(request):
    return request.param


@pytest.fixture(params=(None, 'pilot', 'character'))
def field_name(request):
    return request.param


@pytest.fixture(params=(True, False), ids=('admin', 'not_admin'))
def is_admin(request):
    return request.param


@pytest.fixture(params=(True, False), ids=('reviewer', 'not_reviewer'))
def is_reviewer(request):
    return request.param


@pytest.fixture(params=(True, False), ids=('payer', 'not_payer'))
def is_payer(request):
    return request.param


@pytest.fixture
def user(is_admin, is_reviewer, is_payer):
    user = mock.Mock(id_=2, admin=is_admin)
    permissions = []
    if is_reviewer:
        permissions.extend((
            (100, models.PermissionType.review),
            (200, models.PermissionType.review),))
    if is_payer:
        permissions.extend((
            (200, models.PermissionType.pay),
            (300, models.PermissionType.pay),))
    user.get_permissions.return_value = permissions
    return user


@pytest.fixture(params=(
    'list_personal',
    'list_review',
    'list_pay',
    'list_all'
))
def browse_method(request):
    return request.param


@pytest.fixture
def expected_filter(user, browse_method, add_filter, is_admin, is_reviewer,
                    is_payer):
    expected_filter = sfilter.Search()
    if browse_method == 'list_personal':
        expected_filter.add('user_id', user.id_)
    elif browse_method == 'list_review':
        expected_filter.add('status',
                            models.ActionType.evaluating,
                            models.ActionType.incomplete,
                            models.ActionType.approved)
        if is_reviewer:
            expected_filter.add('division_id', 100, 200)
    elif browse_method == 'list_pay':
        expected_filter.add('status', models.ActionType.approved)
        if is_payer:
            expected_filter.add('division_id', 200, 300)
    elif browse_method == 'list_all':
        if not is_admin:
            if is_reviewer:
                expected_filter.add('division_id', 100, 200)
            if is_payer:
                expected_filter.add('division_id', 200, 300)
    if add_filter:
        expected_filter.add('character_id', 570140137)
    return expected_filter


def test_browse_list(browse_store, add_filter, field_name, user,
                     browse_method, expected_filter):
    browser = users.browse.BrowseActivity(browse_store, user)
    # Set up the browse store mock
    mock_requests = [
        mock.Mock(killmail_id=10),
        mock.Mock(killmail_id=20),
        mock.Mock(killmail_id=30),
    ]
    browse_store.filter_requests.return_value = mock_requests
    browse_store.get_killmails.return_value = mock.sentinel.browse_killmails
    browse_store.filter_sparse.return_value = mock.sentinel.sparse_results
    kwargs = {}
    list_method = getattr(browser, browse_method)
    if field_name is not None:
        kwargs['fields'] = set((field_name,))
    if add_filter:
        filters = sfilter.Search()
        filters.add('character_id', 570140137)
        kwargs['filters'] = filters
    if field_name == 'character':
        with pytest.raises(users.InvalidFieldsError):
            results = list_method(**kwargs)
    else:
        results = list_method(**kwargs)
        if field_name is None:
            browse_store.filter_requests.assert_called_once_with(
                filters=expected_filter)
            browse_store.get_killmails.assert_called_once_with(
                killmail_ids={10, 20, 30})
            assert results == {
                'requests': mock_requests,
                'killmails': mock.sentinel.browse_killmails,
            }
        elif field_name == 'pilot':
            browse_store.filter_sparse.assert_called_once_with(
                filters=expected_filter, fields=set(('pilot',)))
            assert results == mock.sentinel.sparse_results
