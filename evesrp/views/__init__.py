from __future__ import absolute_import
from __future__ import unicode_literals
from flask import redirect, url_for, render_template, make_response, request,\
        json
from flask.ext.login import login_required, current_user
from .. import db
from ..models import Request, ActionType
from ..auth import PermissionType
from ..auth.models import Permission, Division
from ..util import jsonify, varies


@login_required
def index():
    """The index page for EVE-SRP."""
    return redirect(url_for('requests.personal_requests'))


@varies('Accept', 'X-Requested-With')
def error_page(error):
    """View function for displaying error pages."""
    # Try to get some meaningful bits of information about the error
    # HTTPExceptions (raised by abort()) have code and description attributes.
    # Try to prefer those rich values over more generic information.
    code = error.code if hasattr(error, 'code') else 500
    if hasattr(error, 'description'):
        description = error.description
    else:
        description = str(error)
    name = error.name if hasattr(error, 'name') else u'Application Error'
    # Give the error information in a machine readable format for APIs
    if request.is_json or request.is_xhr:
        response_content = jsonify(description=error.description,
                code=code)
    elif request.is_xml:
        pass
    else:
        response_content = render_template('error.html', code=code,
                description=description, name=name, title=code)
    # Give a default response code for generic exceptions
    return make_response(response_content, code)


def request_count(permission, statuses=None):
    """Function intended for counting the number of requests for Jinja
    templates.
    """
    if statuses is None:
        if permission == PermissionType.review:
            statuses = (ActionType.evaluating,)
        elif permission == PermissionType.pay:
            statuses = (ActionType.approved,)
        elif permission == PermissionType.submit:
            statuses = (ActionType.incomplete,)
        else:
            return 0
    elif statuses in ActionType.statuses:
        statuses = (statuses,)
    permissions = current_user.permissions.\
            filter(Permission.permission==permission).\
            subquery()
    divisions = db.session.query(Division.id).\
            join(permissions).\
            subquery()
    requests = db.session.query(db.func.count(db.distinct(Request.id))).\
            join(divisions).\
            filter(Request.status.in_(statuses))
    if permission == PermissionType.submit:
        requests = requests.filter(Request.submitter==current_user)
    return requests.one()[0]


def update_navbar(response):
    if 'application/json' not in response.mimetype:
        return response
    response_json = json.loads(response.get_data())
    counts = {
        'pending': 0,
        'payouts': 0,
        'personal': 0
    }
    response_json['nav_counts'] = counts
    # Unauthenticated users get nothing
    if not current_user.is_authenticated():
        response.set_data(json.dumps(response_json))
        return response
    counts['pending'] = request_count(PermissionType.review)
    counts['payouts'] = request_count(PermissionType.pay)
    counts['personal'] = request_count(PermissionType.submit)
    response.set_data(json.dumps(response_json))
    return response
