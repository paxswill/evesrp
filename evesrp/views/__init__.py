from flask import redirect, url_for, render_template, make_response, request,\
        jsonify
from flask.ext.login import login_required, current_user
from .. import db
from ..models import Request, ActionType
from ..auth import PermissionType
from ..auth.models import Permission, Division


@login_required
def index():
    """The index page for EVE-SRP."""
    return redirect(url_for('requests.personal_requests'))


def error_page(error):
    if request.wants_json or request.is_xhr:
        response_content = jsonify(description=error.description,
                code=error.code)
    else:
        response_content = render_template('error.html', error=error)
    return make_response(response_content, error.code)


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
