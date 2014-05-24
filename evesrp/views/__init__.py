from flask import redirect, url_for, render_template, make_response
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
    return  make_response(render_template('error.html', error=error),
            error.code)


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
    count = db.session.query(db.func.count(Request.id)).\
            join(divisions).\
            filter(Request.status.in_(statuses)).\
            one()[0]
    return count
