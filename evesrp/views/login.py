from __future__ import absolute_import
from base64 import urlsafe_b64decode
import binascii
from flask import render_template, url_for, abort, session, redirect, request,\
        current_app, g, Blueprint
from flask.ext.babel import gettext, lazy_gettext
from flask.ext.login import login_required, logout_user, LoginManager,\
    current_user
from flask.ext.wtf import Form
from six.moves import map
from wtforms.fields import HiddenField
from wtforms.validators import AnyOf
from sqlalchemy.orm.exc import NoResultFound
from .. import csrf, db
from ..auth import AnonymousUser
from ..auth.models import User, APIKey
from ..util import ensure_unicode, jsonify, xmlify


blueprint = Blueprint('login', __name__)


login_manager = LoginManager()
login_manager.anonymous_user = AnonymousUser


@login_manager.user_loader
def login_loader(userid):
    """Pull a user object from the database.

    This is used for loading users from existing sessions.
    """
    return User.query.get(int(userid))


@login_manager.request_loader
def apikey_loader(request):
    api_key = ensure_unicode(request.values.get('apikey'))
    if api_key and request.method == 'GET':
        api_key = api_key.replace(u',', u'=')
        try:
            api_key = urlsafe_b64decode(api_key.encode('utf-8'))
        except binascii.Error:
            # If the api key is malformed, binascii throws an exception.
            # Rejected.
            return None
        try:
            key = APIKey.query.filter_by(key=api_key).one()
        except NoResultFound:
            pass
        else:
            return key.user

    # returning None signifies failure for this method
    return None


class APIKeyForm(Form):
    action = HiddenField(validators=[AnyOf(['add', 'delete'])])
    key_id = HiddenField()


@blueprint.route('/apikeys/', methods=['GET', 'POST'])
@login_required
def api_keys():
    form = APIKeyForm()
    if form.validate_on_submit():
        if form.action.data == 'add':
            key = APIKey(current_user)
        else:
            key = APIKey.query.get(int(form.key_id.data))
            if key is not None:
                db.session.delete(key)
        db.session.commit()
    if request.is_json or request.is_xhr:
        return jsonify(api_keys=current_user.api_keys)
    if request.is_xml:
        return xmlify('apikeys.xml')
    return render_template('apikeys.html', form=form)


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
    return render_template('login.html', forms=forms,
            title=lazy_gettext(u'Log In'))


def localize_login_messages(message):
    return gettext(message)


login_manager.login_view = 'login.login'
login_manager.localize_callback = localize_login_messages


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


@blueprint.route('/logout/')
@login_required
def logout():
    """Logs the current user out.

    Redirects to :py:func:`.index`.
    """
    logout_user()
    return redirect(url_for('index'))
