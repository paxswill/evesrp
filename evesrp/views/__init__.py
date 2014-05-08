from flask import redirect, url_for
from flask.ext.login import login_required


@login_required
def index():
    """The index page for EVE-SRP."""
    return redirect(url_for('requests.personal_requests'))
