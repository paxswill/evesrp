from __future__ import absolute_import
from flask import url_for, render_template, redirect, abort, flash, request,\
        Blueprint, current_app
from flask.ext.babel import gettext, lazy_gettext
from flask.ext.login import login_required, current_user
from flask.ext.wtf import Form
import six
from six.moves import map
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from wtforms.fields import StringField, SubmitField, HiddenField, SelectField,\
        Label
from wtforms.validators import InputRequired, AnyOf, NumberRange

from ..models import db
from ..auth import PermissionType
from ..auth.models import Division, Permission, Entity
from ..util import jsonify, varies


blueprint = Blueprint('divisions', __name__)


@blueprint.route('/')
@login_required
def permissions():
    """Show a page listing all divisions.
    """
    if current_user.admin:
        return render_template('divisions.html',
                divisions=Division.query.all())
    if current_user.has_permission(PermissionType.admin):
        admin_permissions = current_user.permissions.filter_by(
                permission=PermissionType.admin).values(Permission.division_id)
        admin_permissions = map(lambda x: x[0], admin_permissions)
        divisions = db.session.query(Division).\
                filter(Division.id.in_(admin_permissions))
        return render_template('divisions.html', divisions=divisions)
    return render_template('permissions.html')
    return abort(403)


class AddDivisionForm(Form):
    # TRANS: On a form for creating a new division, this is a label for the
    # TRANS: name of the division.
    name = StringField(lazy_gettext(u'Division Name'),
            validators=[InputRequired()])

    # TRANS: On a form for creating a new division, this is a button for
    # TRANS: creating a new division (by submitting the form).
    submit = SubmitField(lazy_gettext(u'Create Division'))


@blueprint.route('/add/', methods=['GET', 'POST'])
@login_required
def add_division():
    """Present a form for adding a division and also process that form.

    Only accesible to adminstrators.
    """
    if not current_user.admin:
        return abort(403)
    form = AddDivisionForm()
    if form.validate_on_submit():
        division = Division(form.name.data)
        db.session.add(division)
        db.session.commit()
        return redirect(url_for('.get_division_details',
            division_id=division.id))
    return render_template('form.html', form=form,
            # TRANS: The title for a page for creating new divisions.
            title=gettext(u'Create Division'))


class ChangeEntity(Form):
    form_id = HiddenField(default='entity')
    id_ = HiddenField()
    name = StringField()
    permission = HiddenField(validators=[AnyOf(list(PermissionType.values()))])
    action = HiddenField(validators=[AnyOf(('add', 'delete'))])


#: List of tuples enumerating attributes that can be transformed/linked.
#: Mainly used as the choices argument to :py:class:`~.SelectField`
transformer_choices = [
    ('', u''),
    # TRANS: Label for fields showing the name of a pilot.
    ('pilot', lazy_gettext(u'Pilot')),
    # TRANS: Label for the corporation a pilot is in.
    ('corporation', lazy_gettext(u'Corporation')),
    # TRANS: Label for the alliance a pilot is in.
    ('alliance', lazy_gettext(u'Alliance')),
    # TRANS: Label for the solar system a loss occured in.
    ('system', lazy_gettext(u'Solar System')),
    # TRANS: Label for the constellation a loss occured in.
    ('constellation', lazy_gettext(u'Constellation')),
    # TRANS: Label for the region a loss occured in.
    ('region', lazy_gettext(u'Region')),
    # TRANS: Label for the type of ship that was lost.
    ('ship_type', lazy_gettext(u'Ship')),
    # TRANS: Label for the status a request is in (ex: Unevaluated, Approved)
    ('status', lazy_gettext(u'Request Status')),
]


class ChangeTransformer(Form):
    form_id = HiddenField(default='transformer')

    # TRANS: The a label for a selection field for selecting which attribute
    # TRANS: to transform. See the translation for 'Attribute Transformer'.
    attribute = SelectField(lazy_gettext(u'Attribute'),
            choices=transformer_choices)

    # TRANS: The label for a selection field for selecting the transformer for
    # TRANS: an attribute. See the translation for 'Attribute Transformer'.
    transformer = SelectField(lazy_gettext(u'Transformer'), choices=[])


def transformer_choices(attr):
    """Conveniece function for generating a list of transformer option tuples.

    :param attr str: the name of the attribute to make a list for.
    :return: A list of tuples suitable for the choices argument of\
        :py:class:`StringField`
    :rtype: list
    """
    default_transformers = [
        ('none', 'None'),
    ]
    choices = default_transformers
    if attr in current_app.url_transformers:
        for transformer in current_app.url_transformers[attr]:
            choices.append((transformer, transformer))
    return choices


@blueprint.route('/<int:division_id>/', methods=['GET'])
@login_required
@varies('Accept', 'X-Requested-With')
def get_division_details(division_id=None, division=None):
    """Generate a page showing the details of a division.

    Shows which groups and individuals have been granted permissions to each
    division.

    Only accesible to administrators.

    :param int division_id: The ID number of the division
    """
    if division is None:
        division = Division.query.get_or_404(division_id)
    if not current_user.admin and not \
            current_user.has_permission(PermissionType.admin, division):
        abort(403)
    if request.is_json or request.is_xhr:
        return jsonify(division._json(True))
    return render_template(
            'division_detail.html',
            division=division,
            entity_form=ChangeEntity(formdata=None),
            transformer_form=ChangeTransformer(formdata=None),
    )


def _modify_division_entity(division):
    """Handle POST requests for adding/removing entities form a Division."""
    form = ChangeEntity()
    if form.validate():
        entity = None
        if form.id_.data != '':
            current_app.logger.debug("Looking up entity by ID: {}".format(
                form.id_.data))
            entity = Entity.query.get(form.id_.data)
            if entity is None:
                # TRANS: This is an error message when there's a problem 
                # TRANS: granting a permission to a user or group
                # TRANS: (collectively called 'entities'). The '#' is not
                # TRANS: special, but the '%s(in_num)d' will be replaced with
                # TRANS: the ID number that was attempted to be added.
                flash(gettext(u"No entity with ID #%(id_num)d.",
                        id_num=form.id_.data),
                    category=u'error')
        else:
            current_app.logger.debug(u"Looking up entity by name: '{}'"\
                    .format(form.name.data))
            try:
                entity = Entity.query.filter_by(
                        name=form.name.data).one()
            except NoResultFound:
                # TRANS: Error message when a user or group with a given name
                # TRANS: cannot be found.
                flash(gettext(u"No entities with the name '%(name)s' found.",
                        name=form.name.data),
                    category=u'error')
            except MultipleResultsFound:
                # TRANS: Error message when multiple users and/or groups are
                # TRANS: found with a given name.
                flash(gettext(
                        u"Multiple entities with the name '%(name)s' found.",
                        name=form.name.data),
                    category=u'error')
            else:
                current_app.logger.debug("entity lookup success")
        if entity is None:
            return get_division_details(division=division), 404, None
        # The entity has been found, create the query for the requested
        # Permission.
        permission_type = PermissionType.from_string(
                form.permission.data)
        permission_query = Permission.query.filter_by(
                division=division,
                entity=entity,
                permission=permission_type)
        # The response for both add and delete actions depends on whether the
        # Permission is found, so look it up first.
        try:
            permission = permission_query.one()
        except NoResultFound:
            if form.action.data == 'add':
                db.session.add(
                    Permission(division, permission_type, entity))
                # TRANS: Message show when granting a permission to a user or
                # TRANS: group.
                flash(gettext(u"%(name)s is now a %(role)s.",
                        name=entity,
                        role=permission_type.description.lower()),
                    category=u"info")
            elif form.action.data == 'delete':
                # TRANS: Message shown when trying to remove a permission from
                # TRANS: a user, but that user didn't have that permission
                # TRANS: already.
                flash(gettext(u"%(name)s is not a %(role)s.",
                        name=entity,
                        role=permission_type.description.lower()),
                    category=u"warning")
        else:
            if form.action.data == 'delete':
                permission_query.delete()
                # TRANS: Confirmation message shown when revoking a permission
                # TRANS: from a user or group.
                flash(gettext(u"%(name)s is no longer a %(role)s.",
                        name=entity,
                        role=permission_type.description.lower()),
                    category=u"info")
            elif form.action.data == 'add':
                flash(gettext(u"%(name)s is now a %(role)s.",
                        name=entity,
                        role=permission_type.description.lower()),
                    category=u"info")
        db.session.commit()
    else:
        for field_name, errors in six.iteritems(form.errors):
            errors = u", ".join(errors)
            # TRANS: Error message that is shown when one or more fields of a
            # TRANS: form are shown.
            flash(gettext(u"Errors for %(field_name)s: %(error)s.",
                field_name=field_name, errors=errors), u'error')
        current_app.logger.info("Malformed entity permission POST: {}".format(
                form.errors))
    return get_division_details(division=division)


def _modify_division_transformer(division):
    """Handle POST requests for changing the Transformers for a Division."""
    form = ChangeTransformer()
    # Set the form's choices
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
        db.session.commit()
        # TRANS: Confirmation message shown when a transformer for an
        # TRANS: attribute has been set.
        flash(gettext(u"'%(attribute)s' set to '%(transformer)s'.",
                attribute=attr, transformer=name), u'message')
    else:
        for field_name, errors in six.iteritems(form.errors):
            errors = u", ".join(errors)
            # TRANS: Generic error message shown for the fields in a form.
            flash(gettext(u"Errors for %(field_name)s: %(error)s.",
                field_name=field_name, errors=errors), u'error')
        current_app.logger.info("Malformed division transformer POST: {}".
                format(form.errors))
    return get_division_details(division=division)


@blueprint.route('/<int:division_id>/', methods=['POST'])
@login_required
def modify_division(division_id):
    """Dispatches modification requests to the specialized view function for
    that operation.
    """
    division = Division.query.get_or_404(division_id)
    if not current_user.admin and not \
            current_user.has_permission(PermissionType.admin, division):
        abort(403)
    form_id = request.form.get('form_id')
    if form_id == 'entity':
        return _modify_division_entity(division)
    elif form_id == 'transformer':
        return _modify_division_transformer(division)
    else:
        current_app.logger.warn("Invalid division modification POST: {}"
                .format(request.form))
        abort(400)


@blueprint.route('/<int:division_id>/transformers/')
@blueprint.route('/<int:division_id>/transformers/<attribute>/')
@login_required
def list_transformers(division_id, attribute=None):
    """API method to get a list of transformers for a division.

    :param division_id int: the ID of the division to look up
    :param attribute str: a specific attribute to look up. Optional.
    :return: JSON
    """
    division = Division.query.get_or_404(division_id)
    if not current_user.admin and not \
            current_user.has_permission(PermissionType.admin, division):
        abort(403)
    if attribute is None:
        attrs = six.iterkeys(current_app.url_transformers)
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
