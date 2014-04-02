from flask import render_template, url_for, abort, session, redirect, request
from flask.ext.login import login_required, logout_user
from flask.ext.principal import identity_changed, AnonymousIdentity

from .. import app, auth_methods

@app.route('/login', methods=['GET', 'POST'])
def login():
    forms = []
    for auth_method in auth_methods:
        prefix = auth_method.__class__.__name__.lower()
        form = auth_method.form()
        forms.append((auth_method, form(prefix=prefix)))
    print(forms)
    if request.method == 'POST':
        for auth_tuple in forms:
            if auth_tuple[1].submit.data:
                auth_method, form = auth_tuple
                break
        else:
            abort(400)
        if form.validate():
            return auth_method.login(form)
    return render_template('login.html', forms=forms)


@app.route('/login/<string:auth_method>/', methods=['GET', 'POST'])
def auth_method_login(auth_method):
    method_map = dict(map(lambda m: (m.__class__.__name__.lower(), m)))
    return method_map[auth_method].view()


@app.route('/logout')
@login_required
def logout():
    logout_user()
    for key in ('identity.name', 'identity.auth_type'):
        session.pop(key, None)
    identity_changed.send(app, identity=AnonymousIdentity())
    return redirect(url_for('index'))


