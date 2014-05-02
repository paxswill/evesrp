from flask import url_for, redirect, abort, request, jsonify, Blueprint
from flask.ext.login import login_required, current_user
from sqlalchemy.orm.exc import NoResultFound

from .. import ships, systems, db
from ..models import db, Request
from ..auth import admin_permission
from ..auth.models import Division, User, Group, Pilot
from .requests import PermissionRequestListing, SubmittedRequestListing


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
    return jsonify(resp)


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
    return jsonify(resp)


@api.route('/request/<int:request_id>/')
@login_required
def request_detail(request_id):
    """Get the details of a request.
    """
    request = Request.query.get_or_404(request_id)
    attrs = ('killmail_url', 'kill_timestamp', 'pilot', 'alliance',
        'corporation', 'submitter', 'division', 'status', 'base_payout',
        'payout', 'details', 'actions', 'modifiers', 'id')
    json = {}
    for attr in attrs:
        if attr == 'payout':
            json[attr] = int(request.payout)
        elif attr == 'pilot':
            json[attr] = request.pilot.name
        else:
            json[attr] = getattr(request, attr)
    json['submit_timestamp'] = request.timestamp
    return jsonify(json)


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
    return jsonify(div_obj)


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
                'href': url_for('requests.request_detail',
                    request_id=request.id),
                'pilot': request.pilot.name,
                'corporation': request.corporation,
                'alliance': request.alliance,
                'ship': request.ship_type,
                'status': request.status,
                'payout': int(payout),
                'payout_str': str(payout),
                'kill_timestamp': request.kill_timestamp,
                'submit_timestamp': request.timestamp,
                'division': request.division.name,
                'submitter_id': request.submitter.id,
                'system': request.system,
            }

        return jsonify(requests=map(request_dict, self.requests()))


class APIRequestListing(FiltersRequestListing, PermissionRequestListing): pass


class APISubmittedListing(FiltersRequestListing, SubmittedRequestListing): pass


@filters.record
def register_request_lists(state):
    # Create the views
    all_requests = APIRequestListing.as_view('filter_requests_all',
            ('submit', 'review', 'pay'),
            ('evaluating', 'approved', 'paid', 'rejected', 'incomplete'))
    submitted_requests = APISubmittedListing.as_view('filter_requests_own')
    review_requests = APIRequestListing.as_view('filter_requests_review',
            ('review',), ('evaluating', 'approved', 'incomplete'))
    pay_requests = APIRequestListing.as_view('filter_requests_pay',
            ('pay',), ('approved',))
    completed_requests = APIRequestListing.as_view('filter_requests_completed',
            ('review', 'pay'), ('paid', 'rejected'))
    # Attach the views to paths
    state.add_url_rule('/requests/', view_func=all_requests)
    state.add_url_rule('/requests/<int:division_id>/', view_func=all_requests)
    state.add_url_rule('/requests/submit/', view_func=submitted_requests)
    state.add_url_rule('/requests/submit/<int:division_id>/',
            view_func=submitted_requests)
    state.add_url_rule('/requests/review/', view_func=review_requests)
    state.add_url_rule('/requests/review/<int:division_id>/',
            view_func=review_requests)
    state.add_url_rule('/requests/pay/', view_func=pay_requests)
    state.add_url_rule('/requests/pay/<int:division_id>/',
            view_func=pay_requests)
    state.add_url_rule('/requests/complete/', view_func=completed_requests)
    state.add_url_rule('/requests/complete/<int:division_id>/',
            view_func=completed_requests)


@filters.route('/ships/')
@login_required
def filter_ships():
    return jsonify(ships=list(ships.ships.values()))


@filters.route('/systems/')
@login_required
def filter_systems():
    return jsonify(systems=list(systems.system_names.values()))


def _first(o):
    return o[0]


@filters.route('/pilots/')
@login_required
def filter_pilots():
    pilots = db.session.query(Pilot.name)
    return jsonify(pilots=map(_first, pilots))


@filters.route('/corporations/')
@login_required
def filter_corps():
    corps = db.session.query(Request.corporation).distinct()
    return jsonify(corporations=map(_first, corps))


@filters.route('/alliances/')
@login_required
def filter_alliances():
    alliances = db.session.query(Request.alliance).distinct()
    return jsonify(alliances=map(_first, alliances))


@filters.route('/divisions/')
@login_required
def filter_divisions():
    div_names = db.session.query(Division.name)
    return jsonify(divisions=map(_first, div_names))
