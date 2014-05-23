from flask import redirect, url_for, render_template
from flask.ext.login import login_required


@login_required
def index():
    """The index page for EVE-SRP."""
    return redirect(url_for('requests.personal_requests'))


def error_page(error):
    return render_template('error.html', error=error)
