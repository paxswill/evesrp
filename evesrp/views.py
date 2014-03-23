from collections import OrderedDict

from flask import render_template, redirect, url_for, request, abort, jsonify,\
        flash
from flask.ext.login import login_user, login_required, logout_user, \
        current_user
from flask.ext.wtf import Form
from wtforms.fields import StringField, PasswordField, SelectField, SubmitField
from wtforms.fields.html5 import URLField, DecimalField
from wtforms.widgets import HiddenInput
from wtforms.validators import InputRequired, ValidationError

from . import app, auth_methods, db
from .auth.models import User, Group, Division

@app.route('/')
@login_required
def index():
    return render_template('base.html')


class SelectValueField(SelectField):
    def _value(self):
        return self.default if self.default is not None else ''


@app.route('/login', methods=['GET', 'POST'])
def login():
    forms = OrderedDict()
    for auth_method in auth_methods:
        form = auth_method.form()
        forms[auth_method.name] = (form, auth_method)
    if request.method == 'POST':
        auth_tuple = forms.get(request.form['auth_method'], None)
        if auth_tuple is not None:
            form = auth_tuple[0]()
        else:
            abort(400)
        if form.validate():
            auth_method = auth_tuple[1]
            return auth_method.login(form)
    template_forms = []
    for key, value in forms.items():
        template_forms.append((key, value[0]()))
    print(template_forms)
    return render_template('login.html', forms=template_forms)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/division')
@login_required
def list_divisions():
    return render_template('divisions.html', divisions=Division.query.all())


class AddDivisionForm(Form):
    name = StringField('Division Name', validators=[InputRequired()])
    submit = SubmitField('Create Division')


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


@app.route('/division/<division_id>/<permission>/add/', methods=['POST'])
@login_required
def division_add_entity(division_id, permission):
    division = Division.query.get_or_404(division_id)
    if request.form['entity_type'] == 'user':
        entity = User.query.filter_by(name=request.form['name']).first()
    elif request.form['entity_type'] == 'group':
        entity = Group.query.filter_by(name=request.form['name']).first()
    else:
        return abort(400)
    if entity is None:
        flash("Cannot find a {} named '{}'.".format(
            request.form['entity_type'], request.form['name']),
            category='error')
    else:
        division.permissions[permission].add(entity)
        db.session.commit()
    return redirect(url_for('division_detail', division_id=division_id))


@app.route('/division/<division_id>/<permission>/<entity>/<entity_id>/delete')
@login_required
def division_delete_entity(division_id, permission, entity, entity_id):
    division = Division.query.get_or_404(division_id)
    if entity == 'user':
        entity = User.query.get_or_404(entity_id)
    elif entity == 'group':
        entity = Group.query.get_or_404(entity_id)
    else:
        return abort(400)
    division.permissions[permission].remove(entity)
    db.session.commit()
    return redirect(url_for('division_detail', division_id=division_id))


@app.route('/submit')
@login_required
def list_submit_requests():
    requests = current_user.requests
    return render_template('list_requests.html', requests=requests)


@app.route('/submit/request', methods=['GET', 'POST'])
@login_required
def submit_request():
    pass
