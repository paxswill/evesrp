from flask import url_for, redirect, abort, request, jsonify, Blueprint
from flask.ext.login import login_required, current_user
from sqlalchemy.orm.exc import NoResultFound

from .. import ships, systems, db
from ..models import Request, ActionType
from ..auth import PermissionType
from ..auth.permissions import admin_permission
from ..auth.models import Division, User, Group, Pilot
from .requests import PermissionRequestListing, PersonalRequests


api = Blueprint('api', __name__)


filters = Blueprint('filters', __name__)


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
        query = db.session.query(User.id, User.name)
    elif entity_type == 'group':
        query = db.session.query(Group.id, Group.name)
    else:
        abort(404)
    json_obj = {
            entity_type + 's': map(
                lambda e: {'id': e.id, 'name': e.name},
                query)
    }
    return jsonify(json_obj)


@api.route('/user/<int:user_id>/')
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    # Set up divisions
    submit = map(lambda p: p.division,
            filter(lambda p: p.permission == PermissionType.submit,
                user.permissions))
    review = map(lambda p: p.division,
            filter(lambda p: p.permission == PermissionType.review,
                user.permissions))
    pay = map(lambda p: p.division,
            filter(lambda p: p.permission == PermissionType.pay,
                user.permissions))
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
    return jsonify(resp)


@api.route('/group/<int:group_id>/')
def group_detail(group_id):
    group = Group.query.get_or_404(group_id)
    submit = map(lambda p: p.division,
            filter(lambda p: p.permission == PermissionType.submit,
                group.permissions))
    review = map(lambda p: p.division,
            filter(lambda p: p.permission == PermissionType.review,
                group.permissions))
    pay = map(lambda p: p.division,
            filter(lambda p: p.permission == PermissionType.pay,
                group.permissions))
    resp = {
        'name': group.name,
        'users': list(group.users),
        'divisions': {
            'submit': list(set(submit)),
            'review': list(set(review)),
            'pay': list(set(pay)),
        },
    }
    return jsonify(resp)


@api.route('/division/')
@login_required
@admin_permission.require()
def list_divisions():
    """List all divisions.
    """
    divisions = db.session.query(Division.id, Division.name)
    return jsonify(divisions=divisions)


@api.route('/division/<int:division_id>/')
@login_required
@admin_permission.require()
def division_detail(division_id):
    """Get the details of a division.

    :param int division_id: The ID of the division
    """
    division = Division.query.get_or_404(division_id)
    permissions = {}
    for perm in PermissionType.all:
        key = perm.name + '_href'
        permissions[key] = url_for('.division_permissions',
                division_id=division_id,
                permission=perm.name)
    return jsonify(
            name=division.name,
            requests=division.requests,
            permissions=permissions)


@api.route('/division/<int:division_id>/<permission>/')
@login_required
@admin_permission.require()
def division_permissions(division_id, permission):
    division = Division.query.get_or_404(division_id)
    permission = PermissionType.from_string(permission)
    # Can't use normal Entity JSON encoder as it doesn't include the
    # authentication source or their type (explicitly. Ain't nobody got time
    # for parsing the entity type out of the href).
    entities = []
    for entity in map(lambda p: p.entity, division.permissions[permission]):
        entity_info = {
            'name': entity.name,
            'id': entity.id,
            'source': str(entity.authmethod),
        }
        if hasattr(entity, 'users'):
            entity_info['type'] = 'Group'
            entity_info['length'] = len(entity.users)
        else:
            entity_info['type'] = 'User'
        entities.append(entity_info)
    return jsonify(
        entities=entities,
        name=permission.name,
        description=permission.description)


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


class FiltersRequestListing(object):
    @property
    def _load_options(self):
        """Returns a sequence of
        :py:class:`~sqlalchemy.orm.strategy_options.Load` objects specifying
        which attributes to load.
        """
        return (
                db.Load(Request).load_only(
                    'id',
                    'pilot_id',
                    'corporation',
                    'alliance',
                    'ship_type',
                    'status',
                    'base_payout',
                    'kill_timestamp',
                    'timestamp',
                    'division_id',
                    'submitter_id',
                    'system',
                ),
                db.Load(Division).joinedload('name'),
                db.Load(Pilot).joinedload('name'),
                db.Load(User).joinedload('id')
        )


    def dispatch_request(self, division_id=None):
        def request_dict(request):
            payout = request.payout
            return {
                'id': request.id,
                'href': url_for('requests.get_request_details',
                    request_id=request.id),
                'pilot': request.pilot.name,
                'corporation': request.corporation,
                'alliance': request.alliance,
                'ship': request.ship_type,
                'status': request.status.name,
                'payout': int(payout),
                'payout_str': str(payout),
                'kill_timestamp': request.kill_timestamp,
                'submit_timestamp': request.timestamp,
                'division': request.division.name,
                'submitter_id': request.submitter.id,
                'system': request.system,
                'constellation': request.constellation,
                'region': request.region,
            }

        return jsonify(requests=map(request_dict, self.requests()))


class APIRequestListing(FiltersRequestListing, PermissionRequestListing): pass


class APIPersonalRequests(FiltersRequestListing, PersonalRequests): pass


@filters.record
def register_request_lists(state):
    # Create the views
    all_requests = APIRequestListing.as_view('filter_requests_all',
            PermissionType.all, ActionType.statuses)
    user_requests = APIPersonalRequests.as_view('filter_requests_own')
    pending_requests = APIRequestListing.as_view('filter_requests_pending',
            (PermissionType.review,), ActionType.pending)
    pay_requests = APIRequestListing.as_view('filter_requests_pay',
            (PermissionType.pay,), (ActionType.approved,))
    completed_requests = APIRequestListing.as_view('filter_requests_completed',
            PermissionType.elevated, ActionType.finalized)
    # Attach the views to paths
    for prefix in state.app.request_prefixes:
        state.add_url_rule(prefix + '/', view_func=all_requests)
        state.add_url_rule(prefix + '/<int:division_id>/',
                view_func=all_requests)
        state.add_url_rule(prefix + '/personal/', view_func=user_requests)
        state.add_url_rule(prefix + '/personal/<int:division_id>/',
                view_func=user_requests)
        state.add_url_rule(prefix + '/pending/', view_func=pending_requests)
        state.add_url_rule(prefix + '/pending/<int:division_id>/',
                view_func=pending_requests)
        state.add_url_rule(prefix + '/pay/', view_func=pay_requests)
        state.add_url_rule(prefix + '/pay/<int:division_id>/',
                view_func=pay_requests)
        state.add_url_rule(prefix + '/completed/',
                view_func=completed_requests)
        state.add_url_rule(prefix + '/completed/<int:division_id>/',
                view_func=completed_requests)


@filters.route('/ship/')
@login_required
def filter_ships():
    return jsonify(ship=list(ships.ships.values()))


@filters.route('/system/')
@login_required
def filter_systems():
    return jsonify(system=list(systems.system_names.values()))


@filters.route('/constellation/')
@login_required
def filter_constellations():
    return jsonify(constellation=list(systems.constellation_names.values()))


@filters.route('/region/')
@login_required
def filter_regions():
    return jsonify(region=list(systems.region_names.values()))


def _first(o):
    return o[0]


@filters.route('/pilot/')
@login_required
def filter_pilots():
    pilots = db.session.query(Pilot.name)
    return jsonify(pilot=map(_first, pilots))


@filters.route('/corporation/')
@login_required
def filter_corps():
    corps = db.session.query(Request.corporation).distinct()
    return jsonify(corporation=map(_first, corps))


@filters.route('/alliance/')
@login_required
def filter_alliances():
    alliances = db.session.query(Request.alliance).distinct()
    return jsonify(alliance=map(_first, alliances))


@filters.route('/division/')
@login_required
def filter_divisions():
    div_names = db.session.query(Division.name)
    return jsonify(division=map(_first, div_names))
