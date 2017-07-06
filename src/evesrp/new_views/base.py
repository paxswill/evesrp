import flask
import flask_login

from evesrp.__version__ import __version__
from evesrp import versioned_static, search_filter
from evesrp import new_models as models


blueprint = flask.Blueprint('jinja', 'evesrp.jinja')
blueprint.add_app_template_global(versioned_static.static_file, 'static_file')
blueprint.add_app_template_global(models.ActionType, 'ActionType')
blueprint.add_app_template_global(models.PermissionType, 'PermissionType')
blueprint.add_app_template_global(models.ModifierType, 'ModifierType')
blueprint.add_app_template_global(__version__, 'app_version')


@blueprint.record_once
def add_site_name(state):
    site_name = state.app.config['SRP_SITE_NAME']
    blueprint.add_app_template_global(site_name, 'site_name')


@blueprint.app_template_global('request_count')
def request_count(permission_type):
    """Function intended for counting the number of requests for Jinja
    templates.

    For :py:attr:`~.PermissionType.review`, it counts requests that the current
    user can see that are in the evaluating status. For
    :py:attr:`~.PermissionType.pay`, it counts requests that the current user
    has access to that are approved, and for :py:attr:`~.PermissionType.submit`
    it counts requests that belong to the current user that are incomplete.

    :type permission_type: :py:class:`evesrp.models.PermissionType`
    :rtype: int
    """
    if permission_type == models.PermissionType.review:
        statuses = (models.ActionType.evaluating,)
    elif permission_type == models.PermissionType.pay:
        statuses = (models.ActionType.approved,)
    elif permission_type == models.PermissionType.submit:
        statuses = (models.ActionType.incomplete,)
    else:
        return 0
    store = flask.current_app.store
    user_permissions = flask_login.current_user.get_permissions(store)
    permission_tuples = map(lambda p: p.to_tuple(), user_permissions)
    division_ids = [perm[1] for perm in permission_tuples
                    if perm[0] == permission_type]
    search = search_filter.Search()
    search.add_filter('status', *statuses)
    search.add_filter('division_id', *division_ids)
    if permission_type == models.PermissionType.submit:
        search.add_filter('user_id', flask_login.current_user.user.id_)
    request_ids = set(store.filter_sparse(search, {'request_id', }))
    return len(request_ids)
