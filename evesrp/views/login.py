from flask import render_template, url_for, abort, session, redirect, request,\
        current_app, g, Blueprint
from flask.ext.login import login_required, logout_user, LoginManager
from flask.ext.principal import identity_changed, AnonymousIdentity
from .. import csrf


blueprint = Blueprint('login', __name__)


login_manager = LoginManager()


@blueprint.route('/login/', methods=['GET', 'POST'])
def login():
    """Presents the login form and processes responses from that form.

    When a POST request is recieved, this function passes control to the
    appropriate :py:meth:`login <evesrp.auth.AuthMethod.login>` method.
    """
    # forms is a list of tuples. The tuples are
    # (AuthMethod instance, AuthForm instance)
    forms = []
    for auth_method in current_app.auth_methods:
        prefix = auth_method.safe_name
        form = auth_method.form()
        forms.append((auth_method, form(prefix=prefix)))
    if request.method == 'POST':
        # Find the form that was submitted. The unique prefix for each form
        # means only one form.submit is going to be valid.
        for auth_tuple in forms:
            if auth_tuple[1].submit.data:
                auth_method, form = auth_tuple
                break
        else:
            abort(400)
        if form.validate():
            return auth_method.login(form)
    return render_template('login.html', forms=forms)


login_manager.login_view = 'login.login'


# 302 redirects let the request method change to GET if it started as POST.
# By defining routes for both of these paths, the implicit redirect for the
# first route is skipped.
@blueprint.route('/login/<string:auth_method>', methods=['GET', 'POST'])
@blueprint.route('/login/<string:auth_method>/', methods=['GET', 'POST'])
def auth_method_login(auth_method):
    """Trampoline for :py:class:`~evesrp.auth.AuthMethod`\-specific views.

    See :py:meth:`Authmethod.view <evesrp.auth.AuthMethod.view>` for more
    details.
    """
    method_map = dict(map((lambda m: (m.safe_name, m)),
        current_app.auth_methods))
    return method_map[auth_method].view()

auth_method_login.methods = ['GET', 'POST']


@blueprint.route('/logout/')
@login_required
def logout():
    """Logs the current user out.

    Redirects to :py:func:`.index`.
    """
    logout_user()
    for key in ('identity.name', 'identity.auth_type'):
        session.pop(key, None)
    identity_changed.send(current_app._get_current_object(),
            identity=AnonymousIdentity())
    return redirect(url_for('index'))
