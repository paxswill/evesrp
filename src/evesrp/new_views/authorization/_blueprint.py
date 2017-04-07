import flask
import flask_babel
import flask_login
import flask_wtf
import six
import wtforms

from evesrp import storage, users, util
from evesrp import new_models as models
from .. import util as views_util


blueprint = flask.Blueprint('authz', 'evesrp.new_views.authorization',
                            template_folder='templates')


class AddDivisionForm(flask_wtf.FlaskForm):
    # TRANS: On a form for creating a new division, this is a label for the
    # TRANS: name of the division.
    name = wtforms.fields.StringField(
        flask_babel.lazy_gettext(u'Division Name'),
        validators=[wtforms.validators.InputRequired()])


@blueprint.route('/', methods=['GET', 'POST'])
@flask_login.fresh_login_required
def permissions():
    activity = users.PermissionsAdmin(flask.current_app.store,
                                      flask_login.current_user.user)
    form = AddDivisionForm()
    if flask.request.method == 'POST':
        if form.validate():
            try:
                division = activity.create_division(form.name.data)
            except users.AdminPermissionError:
                abort(403)
            return flask.redirect(flask.url_for('.get_division',
                                                division_id=division.id_))
    else:
        permissions = activity.list_permissions()
        admin_divisions = [d for d, p in six.iteritems(permissions)
                           if models.PermissionType.admin in p]
        template_args = {'activity': activity}
        if flask_login.current_user.admin:
            template_args['form'] = form
        return flask.render_template('divisions.html', activity=activity,
                                     form=form)


@blueprint.route('/entities/', methods=['GET'])
@flask_login.fresh_login_required
def list_entities():
    activity = users.PermissionsAdmin(flask.current_app.store,
                                      flask_login.current_user.user)
    try:
        entities = activity.list_entities()
    except users.AdminPermissionError:
        flask.abort(403)

    def serialize_entity(entity):
        data = {
            'id': entity.id_,
            'name': entity.name,
        }
        if isinstance(entity, models.User):
            data['type'] = 'user'
            data['admin'] = entity.admin
        elif isinstance(entity, models.Group):
            data['type'] = 'group'
        return data
    json_entities = [serialize_entity(e) for e in entities]
    return util.jsonify(entities=json_entities)


class ChangeEntity(flask_wtf.FlaskForm):

    form_id = wtforms.fields.HiddenField(default='entity')

    id_ = wtforms.fields.HiddenField(validators=[
        wtforms.validators.InputRequired(),
    ])

    permission = wtforms.fields.HiddenField(validators=[
        wtforms.validators.AnyOf([p.name for p in models.PermissionType])
    ])

    action = wtforms.fields.HiddenField(validators=[
        wtforms.validators.AnyOf(('add', 'delete'))
    ])


@blueprint.route('/<int:division_id>/', methods=['GET'])
@flask_login.fresh_login_required
def get_division(division_id):
    store = flask.current_app.store
    division = store.get_division(division_id)
    try:
        activity = users.DivisionAdmin(store, flask_login.current_user.user,
                                       division)
    except users.AdminPermissionError:
        flask.abort(403)
    form = ChangeEntity()
    return flask.render_template('division_detail.html',
                                 activity=activity,
                                 entity_form=form)


@blueprint.route('/<int:division_id>/', methods=['POST'])
@flask_login.fresh_login_required
def modify_division(division_id):
    form = ChangeEntity()
    if form.validate():
        try:
            entity = store.get_entity(int(form.id_.data))
        except storage.NotFoundError:
            # TRANS: This is an error message when there's a problem 
            # TRANS: granting a permission to a user or group
            # TRANS: (collectively called 'entities'). The '#' is not
            # TRANS: special, but the '%s(in_num)d' will be replaced with
            # TRANS: the ID number that was attempted to be added.
            flask.flash(flask_babel.gettext(u"No entity with ID #%(id_num)d.",
                                            id_num=form.id_.data),
                        category=u'error')
        else:
            permission_type = models.PermissionType[form.permission.data]
            pretty_permission = views_util.pretty_permission(permission_type)
            # N.B. The old EVE-SRP implementation responded with an error if
            # adding a permission that was already granted, or removing one
            # that wasn't there. The new version does not care, and will
            # respond with a success in any case.
            if form.action.data == 'add':
                activity.add_permission(entity, permission)
                # TRANS: Message show when granting a permission to a user or
                # TRANS: group.
                flask.flash(flask_babel.gettext(
                    u"%(name)s is now a %(role)s.", name=entity.name,
                    role=pretty_permission.lower()),
                            category=u"info")
            elif form.action.data == 'delete':
                activity.remove_permission(entity, permission)
                # TRANS: Confirmation message shown when revoking a permission
                # TRANS: from a user or group.
                flask.flash(flask_babel.gettext(
                    u"%(name)s is no longer a %(role)s.", name=entity.name,
                    role=pretty_permission.lower()),
                            category=u"info")
    else:
        for field_name, errors in six.iteritems(form.errors):
            errors = u", ".join(errors)
            # TRANS: Error message that is shown when one or more fields of a
            # TRANS: form are shown.
            flask.flash(flask_babel.gettext(
                u"Errors for %(field_name)s: %(error)s.",
                field_name=field_name,
                error=errors),
                        u'error')

    return flask.render_template('division_detail.html',
                                 activity=activity,
                                 entity_form=form)
