from flask import url_for, render_template, redirect, abort, flash, request,\
        Blueprint, current_app
from flask.ext.login import login_required
from flask.ext.wtf import Form
from wtforms.fields import StringField, SubmitField, HiddenField, SelectField,\
        Label
from wtforms.validators import InputRequired, AnyOf, NumberRange
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

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
    form_id = HiddenField(default='entity')
    id_ = HiddenField()
    name = StringField()
    permission = HiddenField(validators=[AnyOf(('submit', 'review', 'pay'))])
    action = HiddenField(validators=[AnyOf(('add', 'delete'))])


class SetTransformer(Form):
    form_id = HiddenField(default='transformer')
    name = SelectField()
    kind = HiddenField()


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
    ship_transformers = [('none', 'None')]
    for name in current_app.ship_urls.keys():
        ship_transformers.append((name, name))
    pilot_transformers = [('none', 'None')]
    for name in current_app.pilot_urls.keys():
        pilot_transformers.append((name, name))
    if request.method == 'POST':
        if request.form['form_id'] == 'entity':
            form = ChangeEntity()
            if form.validate():
                if form.id_.data != '':
                    entity = Entity.query.get(form.id_.data)
                    if entity is None:
                        flash("No entity with ID #{}.".format(form.id_.data), 'error')
                else:
                    try:
                        entity = Entity.query.filter_by(name=form.name.data).one()
                    except NoResultFound:
                        flash("No entities with the name '{}' found.".
                                format(form.name.data), category='error')
                    except MultipleResultsFound:
                        flash("Multiple entities eith the name '{}' found.".
                                format(form.name.data), category='error')
                if form.action.data == 'add':
                    perm = Permission(division, form.permission.data, entity)
                    db.session.add(perm)
                    flash("Added '{}'.".format(entity))
                elif form.action.data == 'delete':
                    Permission.query.filter_by(division=division,
                            permission=form.permission.data, entity=entity).delete()
                    flash("Removed '{}' from '{}'.".format(form.permission.data,
                            entity))
        elif request.form['form_id'] == 'transformer':
            form = SetTransformer()
            if form.kind.data == 'ship':
                form.name.choices = ship_transformers
            elif form.kind.data == 'pilot':
                form.name.choices = pilot_transformers
            if form.validate():
                if form.kind.data == 'ship':
                    if form.name.data == 'none':
                        division.ship_transformer = None
                    else:
                        transformer = current_app.ship_urls[form.name.data]
                        division.ship_transformer = transformer
                elif form.kind.data == 'pilot':
                    if form.name.data == 'none':
                        division.pilot_transformer = None
                    else:
                        transformer = current_app.pilot_urls[form.name.data]
                        division.pilot_transformer = transformer
        db.session.commit()
    ship_form = SetTransformer(formdata=None)
    ship_form.name.label = Label(ship_form.name.id, 'Ship Transformers')
    ship_form.name.choices = ship_transformers
    ship_transformer = division.ship_transformer
    if ship_transformer is not None:
        ship_form.name.data = ship_transformer.name
    pilot_form = SetTransformer(formdata=None)
    pilot_form.name.label = Label(pilot_form.name.id, 'Pilot Transformers')
    pilot_form.name.choices = pilot_transformers
    pilot_transformer = division.pilot_transformer
    if pilot_transformer is not None:
        pilot_form.name.data = pilot_transformer.name
    return render_template(
            'division_detail.html',
            division=division,
            entity_form=ChangeEntity(),
            ship_form=ship_form,
            pilot_form=pilot_form
    )
