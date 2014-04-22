from flask import url_for, render_template, redirect, abort, flash, request,\
        Blueprint
from flask.ext.login import login_required
from flask.ext.wtf import Form
from wtforms.fields import StringField, SubmitField, HiddenField
from wtforms.validators import InputRequired, AnyOf, NumberRange
from sqlalchemy.orm.exc import NoResultFound

from ..models import db
from ..auth import admin_permission
from ..auth.models import Division, Permission, Entity


blueprint = Blueprint('divisions', __name__)


@blueprint.route('/')
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


@blueprint.route('/add/', methods=['GET', 'POST'])
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
        return redirect(url_for('.division_detail', division_id=division.id))
    return render_template('form.html', form=form)


class ChangeEntity(Form):
    id_ = HiddenField()
    name = StringField()
    permission = HiddenField(validators=[AnyOf(('submit', 'review', 'pay'))])
    action = HiddenField(validators=[AnyOf(('add', 'delete'))])


@blueprint.route('/<int:division_id>/', methods=['GET', 'POST'])
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
        if form.action.data == 'add':
            try:
                entity = Entity.query.filter_by(name=form.name.data).one()
            except NoResultFound:
                flash("No user with the name '{}' found.".
                        format(form.name.data), category='error')
            else:
                perm = Permission(division, form.permission.data, entity)
                db.session.add(perm)
                flash("Added '{}'.".format(entity))
        elif form.action.data == 'delete':
            entity = Entity.query.get(form.id_.data)
            if entity is None:
                flash("No entity with ID '{}' found.".format(form.id_.data),
                        category='error')
            else:
                Permission.query.filter_by(division=division,
                        permission=form.permission.data,
                        entity=entity).delete()
                flash("Removed '{}' from '{}'.".format(form.permission.data,
                        entity))
        db.session.commit()
    return render_template('division_detail.html', division=division,
        form=form)
