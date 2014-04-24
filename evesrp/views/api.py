from flask import url_for, redirect, abort, request, jsonify, Blueprint
from flask.ext.login import login_required
from sqlalchemy.orm.exc import NoResultFound

from .. import ships
from ..models import db, Request
from ..auth import admin_permission
from ..auth.models import Division, User, Group


api = Blueprint('api', __name__)




@api.route('/<entity_type>/')
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


@api.route('/user/<int:user_id>/')
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    # Set up divisions
    submit = map(lambda p: p.division,
            filter(lambda p: p.permission == 'submit', user.permissions))
    review = map(lambda p: p.division,
            filter(lambda p: p.permission == 'review', user.permissions))
    pay = map(lambda p: p.division,
            filter(lambda p: p.permission == 'pay', user.permissions))
    resp = {
        'name': user.name,
        'groups': list(user.groups),
        'divisions': {
            'submit': list(set(submit)),
            'review': list(set(review)),
            'pay': list(set(pay)),
        },
        'admin': user.admin,
        'requests': user.requests,
    }
    return jsonify(**resp)


@api.route('/group/<int:group_id>/')
def group_detail(group_id):
    group = Group.query.get_or_404(group_id)
    submit = map(lambda p: p.division,
            filter(lambda p: p.permission == 'submit', group.permissions))
    review = map(lambda p: p.division,
            filter(lambda p: p.permission == 'review', group.permissions))
    pay = map(lambda p: p.division,
            filter(lambda p: p.permission == 'pay', group.permissions))
    resp = {
        'name': group.name,
        'users': list(group.users),
        'divisions': {
            'submit': list(set(submit)),
            'review': list(set(review)),
            'pay': list(set(pay)),
        },
    }
    return jsonify(**resp)


@api.route('/request/<int:request_id>/')
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


@api.route('/division/')
@login_required
@admin_permission.require()
def list_divisions():
    """List all divisions.
    """
    return jsonify(divisions=Division.query.all())


@api.route('/division/<int:division_id>/')
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


@api.route('/ships/')
@login_required
def ship_list():
    """Get an array of objects corresponding to every ship type.

    The objects have two keys, ``id`` is the integer typeID, and ``name`` is
    the name of the ship. This method is only accessible for logged in users to
    try to keep possible misuse to a minimum.
    """
    ship_objs = list(map(lambda s: {'name': s[1], 'id': s[0]},
            ships.ships.items()))
    return jsonify(ships=ship_objs)
