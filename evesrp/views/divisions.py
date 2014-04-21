from flask import url_for, render_template, redirect, abort, flash, request
from flask.ext.login import login_required
from flask.ext.wtf import Form
from wtforms.fields import StringField, SubmitField, HiddenField
from wtforms.validators import InputRequired, AnyOf, NumberRange
from sqlalchemy.orm.exc import NoResultFound

from ..models import db
from ..auth import admin_permission
from ..auth.models import Division, User, Group


@login_required
@admin_permission.require()
def list_divisions():
    """Show a page listing all divisions.

    Accesible only to administrators.
    """
    return render_template('divisions.html', divisions=Division.query.all())


class AddDivisionForm(Form):
    name = StringField('Division Name', validators=[InputRequired()])
    submit = SubmitField('Create Division')


@login_required
@admin_permission.require()
def add_division():
    """Present a form for adding a view and also process that form.

    Only accesible to adminstrators.
    """
    form = AddDivisionForm()
    if form.validate_on_submit():
        division = Division(form.name.data)
        db.session.add(division)
        db.session.commit()
        return redirect(url_for('division_detail', division_id=division.id))
    return render_template('form.html', form=form)

add_division.methods = ['GET', 'POST']


class ChangeEntity(Form):
    id_ = HiddenField(validators=[NumberRange(min=0)])
    type_ = HiddenField(validators=[AnyOf('user', 'group')])
    permission = HiddenField(validators=[AnyOf('submit', 'review', 'pay')])
    action = HiddenField(validators=[AnyOf('add', 'delete')])


@login_required
@admin_permission.require()
def division_detail(division_id):
    """Generate a page showing the details of a division.

    Shows which groups and individuals have been granted permissions to each
    division.

    Only accesible to administrators.

    :param int division_id: The ID number of the division
    """
    division = Division.query.get_or_404(division_id)
    form = ChangeEntity()
    if form.validate_on_submit():
        consistent = True
        if form.type_.data == 'user':
            try:
                entity = User.query.get(form.id_.data)
            except NoResultFound:
                flash("No User for the ID {} found".
                        format(form.id_.data), category='error')
                consistent = False
        elif form.type_.data == 'group':
            try:
                entity = Group.query.get(form.id_.data)
            except NoResultFound:
                flash("No Group for the ID {} found.".
                        format(form.id_.data), category='error')
                consistent = False
        if consistent:
            if form.action.data == 'add':
                division.permissions[form.permission.data].add(entity)
            elif form.action.data == 'delete':
                division.permissions[form.permission.data].remove(entity)
            flash("Added '{}'.".format(entity))
            db.session.commit()
    return render_template('division_detail.html', division=division,
        form=form)

division_detail.methods = ['GET', 'POST']


@login_required
@admin_permission.require()
def division_permission(division_id, permission):
    # external API method. It's the only one implemented so far, so just ignore
    # it for now.
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


@login_required
@admin_permission.require()
def division_add_entity(division_id, permission):
    """Utility path for granting permissions to an entity in a division.

    Redirects to the :py:func:`detail page <division_detail>` for the division
    being operated on.

    Only accesible to admins.

    :param int division_id: The ID of the division
    :param str permission: The permission being granted
    """
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

division_add_entity.methods = ['POST']


@login_required
@admin_permission.require()
def division_delete_entity(division_id, permission, entity, entity_id):
    """Utility path for removing a permission for an entity.

    Redirects to the :py:func:`details <division_detail>` for the division
    being operated on.

    Accesible only to admins.

    :param int division_id: The division ID number
    :param str permission: The permission to remove
    :param str entity: What kind of entity to remove ('group' or 'user')
    :param int entity_id: The ID number of the user or group to remove
    """
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
