from flask import render_template, redirect, url_for, request, abort, jsonify
from flask.ext.login import login_user, login_required, logout_user
from flask.ext.wtf import Form
from wtforms.fields import StringField, PasswordField, SelectField, SubmitField
from wtforms.widgets import HiddenInput
from wtforms.validators import InputRequired

from . import app, auth_methods, db

from .auth.models import Division

@app.route('/')
@login_required
def index():
    return render_template('base.html')


class SelectValueField(SelectField):
    def _value(self):
        return self.default if self.default is not None else ''


class LoginForm(Form):
    username = StringField('Username', validators=[InputRequired()])
    password = PasswordField('Password', validators=[InputRequired()])
    auth_method = SelectValueField('Authentication Source', default=0,
            choices=[(i, m.method_name) for i, m in enumerate(auth_methods)],
            coerce=int)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if len(auth_methods) < 2:
        form.auth_method.widget = HiddenInput()
    if form.validate_on_submit():
        method = auth_methods[form.auth_method.data]
        user = method.authenticate_user(form.username.data, form.password.data)
        if user is not None:
            login_user(user)
            return redirect(request.args.get('next') or url_for('index'))
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/divisions')
@login_required
def list_divisions():
    return render_template('divisions.html', divisions=Division.query.all())


class AddDivisionForm(Form):
    name = StringField('Division Name', validators=[InputRequired()])


@app.route('/division/add', methods=['GET', 'POST'])
@login_required
def add_division():
    form = AddDivisionForm()
    if form.validate_on_submit():
        division = Division(form.name.data)
        db.session.add(division)
        db.session.commit()
        return redirect(url_for('division_detail', division_id=division.id))
    return render_template('form.html', form=form)


@app.route('/division/<division_id>')
@login_required
def division_detail(division_id):
    division = Division.query.get_or_404(division_id)
    return render_template('division_detail.html', division=division)


@app.route('/division/<division_id>/<permission>')
@login_required
def division_permission(division_id, permission):
    division = Division.query.get_or_404(division_id)
    users = []
    for user in division.permissions[permission].individuals:
        user_dict = {
                'name': user.name,
                'id': user.id
                }
        users.append(user_dict)
    groups = []
    for group in division.permissions[permission].groups:
        group_dict = {
                'name': group.name,
                'id': group.id,
                'size': len(group.individuals)
                }
        groups.append(group_dict)
    return jsonify(name=division.name,
            groups=groups,
            users=users)
