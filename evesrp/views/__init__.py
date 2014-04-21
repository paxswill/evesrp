from flask import render_template
from flask.ext.login import login_required


@login_required
def index():
    """The index page for EVE-SRP."""
    return render_template('base.html')
