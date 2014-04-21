from flask import render_template
from flask.ext.login import login_required

from . import login, divisions, requests


@login_required
def index():
    """The index page for EVE-SRP."""
    return render_template('base.html')


def connect_views(app):
    """Add routes to the views to an app.

    :param app: The app to add the routes to
    :type app: :py:class:`flask.Flask`
    """
    # Base views
    app.add_url_rule(rule='/', view_func=index)
    # Login views
    app.add_url_rule(rule='/login/', view_func=login.login)
    app.add_url_rule(rule='/login/<string:auth_method>/',
            view_func=login.auth_method_login)
    app.add_url_rule(rule='/logout/', view_func=login.logout)
    # Requests views
    submit_view = login_required(
            requests.SubmittedRequestListing.as_view('list_submit_requests'))
    app.add_url_rule('/submit/', view_func=submit_view)
    app.add_url_rule('/submit/<int:division_id>', view_func=submit_view)
    requests.register_perm_request_listing(app, 'list_review_requests',
            '/review/', ('review',), (lambda r: not r.finalized))
    requests.register_perm_request_listing(app, 'list_approved_requests',
            '/pay/', ('pay',), (lambda r: r.status == 'approved'))
    requests.register_perm_request_listing(app, 'list_completed_requests',
            '/complete/', ('review', 'pay'), (lambda r: r.finalized))
    app.add_url_rule(rule='/submit/request/',
            view_func=requests.submit_request)
    app.add_url_rule(rule='/request/<int:request_id>/',
            view_func=requests.request_detail)
