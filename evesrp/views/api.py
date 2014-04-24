from flask import url_for, redirect, abort, request, jsonify, Blueprint
from flask.json import JSONEncoder
from flask.ext.login import login_required
from sqlalchemy.orm.exc import NoResultFound

from ..models import db, Request
from ..auth import admin_permission
from ..auth.models import Division, User, Group


blueprint = Blueprint('api', __name__)


class SRPEncoder(JSONEncoder):
    def default(self, o):
        try:
            ret = {
                    'name': o.name,
                    'id': o.id,
            }
        except AttributeError:
            try:
                ret = {
                        'id': o.id,
                }
            except AttributeError:
                # There is nothing I can do for you...
                pass
            else:
                if isinstance(o, Request):
                    ret['href'] = url_for('api.request_detail',
                            request_id=o.id)
                return ret
        else:
            if isinstance(o, User):
                ret['href'] = url_for('api.user_detail', user_id=o.id)
            elif isinstance(o, Group):
                ret['href'] = url_for('api.group_detail', group_id=o.id)
            elif isinstance(o, Division):
                ret['href'] = url_for('api.division_detail', division_id=o.id)
            elif isinstance(o, Request):
                ret['href'] = url_for('api.request_detail', request_id=o.id)
            return ret
        return super(SRPEncoder, self).default(o)


@blueprint.route('/<entity_type>/')
@login_required
@admin_permission.require()
def list_entities(entity_type):
    """Return a JSON object with a list of all of the specified entity type.

    Example output::
        {
          groups: [
            {name: 'Bar', id: 1},
            {name: 'Foo', id: 0},
            {name: 'Baz', id: 20}
          ]
        }

    Order of the objects in the ``'users'`` or ``groups`` key is undefined.

    This method is only accesible to administrators.

    :param str entity_type: Either ``'user'`` or ``'group'``.
    """
    if entity_type == 'user':
        query = User.query
    elif entity_type == 'group':
        query = Group.query
    else:
        abort(404)
    json_obj = {
        entity_type + 's': query.all(),
    }
    return jsonify(**json_obj)


@blueprint.route('/user/<int:user_id>/')
def user_detail(user_id):
    pass


@blueprint.route('/group/<int:group_id>/')
def group_detail(group_id):
    group = Group.query.get_or_404(group_id)
    resp = {
        'name': group.name,
        'users': group.users,
        'divisions': group.divisions,
    }
    return jsonify(**resp)


@blueprint.route('/request/<int:request_id>/')
@login_required
def request_detail(request_id):
    """Get the details of a request.
    """
    request = Request.query.get_or_404(request_id)
    attrs = ('killmail_url', 'kill_timestamp', 'pilot', 'alliance',
        'corporation', 'submitter', 'division', 'status', 'base_payout',
        'payout', 'details', 'actions', 'modifiers', 'id')
    json_obj = []
    for attr in attrs:
        json_obj[attr] = getattr(request, attr)
    json_obj['submit_timestamp'] = request.timestamp
    return jsonify(json_obj)


@blueprint.route('/division/')
@login_required
@admin_permission.require()
def list_divisions():
    """List all divisions.
    """
    return jsonify(divisions=Division.query.all())


@blueprint.route('/division/<int:division_id>/')
@login_required
@admin_permission.require()
def division_detail(division_id):
    """Get the details of a division.

    :param int division_id: The ID of the division
    """
    division = Division.query.get_or_404(division_id)
    div_obj = {
            'name': division.name,
            'requests': division.requests,
    }
    permissions = {}
    for perm in ('submit', 'review', 'pay'):
        permission = division.permissions[perm]
        permissions[perm] = {
                'users': permission.individuals,
                'groups': permission.groups,
        }
    return jsonify(**div_obj)


@login_required
@admin_permission.require()
def division_permission(division_id, permission):
    # external API method. It's the only one implemented so far, so just ignore
    # it for now.
    division = Division.query.get_or_404(division_id)
    users = []
    for user in division.permissions[permission].individuals:
        user_dict = {
                'name': user.name,
                'id': user.id
                }
        users.append(user_dict)
    groups = []
    for group in division.permissions[permission].groups:
        group_dict = {
                'name': group.name,
                'id': group.id,
                'size': len(group.individuals)
                }
        groups.append(group_dict)
    return jsonify(name=division.name,
            groups=groups,
            users=users)


