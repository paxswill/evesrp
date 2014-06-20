from flask import url_for, render_template, redirect, abort, flash, request,\
        Blueprint, current_app, jsonify
from flask.ext.login import login_required
from flask.ext.wtf import Form
from wtforms.fields import StringField, SubmitField, HiddenField, SelectField,\
        Label
from wtforms.validators import InputRequired, AnyOf, NumberRange
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from ..models import db
from ..auth.permissions import admin_permission
from ..auth import PermissionType
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
    permission = HiddenField(validators=[AnyOf(PermissionType.values())])
    action = HiddenField(validators=[AnyOf(('add', 'delete'))])


transformer_choices = [
    ('', ''),
    ('kill_timestamp', 'Kill Timestamp'),
    ('pilot', 'Pilot'),
    ('corporation', 'Corporation'),
    ('alliance', 'Alliance'),
    ('system', 'Solar System'),
    ('constellation', 'Constellation'),
    ('region', 'Region'),
    ('ship_type', 'Ship'),
    ('payout', 'Payout'),
    ('status', 'Request Status'),
]


class ChangeTransformer(Form):
    form_id = HiddenField(default='transformer')
    attribute = SelectField('Attribute', choices=transformer_choices)
    transformer = SelectField('Transformer', choices=[])


def transformer_choices(attr):
    default_transformers = [
        ('none', 'None'),
    ]
    choices = default_transformers
    if attr in current_app.url_transformers:
        for transformer in current_app.url_transformers[attr]:
            choices.append((transformer, transformer))
    return choices


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
                permission = PermissionType.from_string(form.permission.data)
                if form.action.data == 'add':
                    db.session.add(Permission(division, permission, entity))
                    flash("'{}' is now a {}.".format(entity,
                            permission.description.lower()), "info")
                elif form.action.data == 'delete':
                    Permission.query.filter_by(division=division,
                            permission=permission, entity=entity).delete()
                    flash("'{}' is no longer a {}.".format(entity,
                            permission.description.lower()), "info")
            else:
                abort(400)
        elif request.form['form_id'] == 'transformer':
            form = ChangeTransformer()
            attr = form.attribute.data
            form.transformer.choices = transformer_choices(attr)
            # Check form and go from there
            if form.validate():
                name = form.transformer.data
                if name == 'none':
                    division.transformers[attr] = None
                else:
                    # Get the specific map of transformers for the attribute
                    attr_transformers = current_app.url_transformers[attr]
                    # Get the new transformer
                    division.transformers[attr] = attr_transformers[name]
                    # Explicitly add the TransformerRef to the session
                    db.session.add(division.division_transformers[attr])
            else:
                abort(400)
        db.session.commit()
    return render_template(
            'division_detail.html',
            division=division,
            entity_form=ChangeEntity(),
            transformer_form=ChangeTransformer(),
    )


@blueprint.route('/<int:division_id>/transformers/')
@blueprint.route('/<int:division_id>/transformers/<attribute>/')
@login_required
@admin_permission.require()
def list_transformers(division_id, attribute=None):
    division = Division.query.get_or_404(division_id)
    if attribute is None:
        attrs = current_app.url_transformers.keys()
    else:
        attrs = (attribute,)
    choices = {}
    for attr in attrs:
        raw_choices = transformer_choices(attr)
        current = division.transformers.get(attr, None)
        if current is not None:
            choices[attr] = \
                    [(c[0], c[1], c[1] == current.name) for c in raw_choices]
        else:
            choices[attr] = \
                    [(c[0], c[1], False) for c in raw_choices]
    return jsonify(choices)
