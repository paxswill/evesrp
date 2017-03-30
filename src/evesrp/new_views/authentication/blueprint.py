import base64
import collections

import flask
import flask_babel
import flask_login
import flask_wtf
import six
import wtforms

from evesrp import storage, util
from evesrp import new_auth as authn
from .user import LoginUser




authn_blueprint = flask.Blueprint('authn', 'evesrp.new_views.authentication',
                                  template_folder='templates',
                                  static_folder='static',
                                  static_url_path='/static/authn')


login_manager = flask_login.LoginManager()
login_manager.login_view = 'authn.login'
login_manager.localize_callback = flask_babel.gettext


@authn_blueprint.record_once
def attach_login_manager(state):
    login_manager.init_app(state.app)


@login_manager.user_loader
def login_loader(userid):
    store = flask.current_app.store
    # Make sure the given userid is an int
    try:
        user_id = int(userid)
    except ValueError:
        return None
    try:
        user = store.get_user(user_id)
    except storage.NotFoundError:
        return None
    return LoginUser(user)


def create_providers(app):
    providers = collections.OrderedDict()
    for provider_data in app.config['SRP_AUTH_METHODS']:
        provider_data = provider_data.copy()
        provider_data['store'] = app.store
        provider = util.instance_from_dict(provider_data)
        providers[provider.uuid] = provider
    return providers


def form_for_provider(provider):
    fields = collections.OrderedDict()
    for field_name, field_type in six.iteritems(provider.fields):
        # Coax field_name into something nice for the user
        pretty_name = field_name.replace('_', ' ')
        pretty_name = pretty_name.capitalize()
        # Different field types gen different Field instances
        if field_type == authn.LoginFieldType.string:
            field = wtforms.fields.StringField(pretty_name, validators=[
                wtforms.validators.InputRequired()
            ])
        elif field_type == authn.LoginFieldType.password:
            field = wtforms.fields.PasswordField(pretty_name, validators=[
                wtforms.validators.InputRequired()
            ])
        elif field_name == u'submit':
            if isinstance(field_type, tuple):
                # field_type is used as a label for the 'submit' button.
                # if it's a tuple, instead of a button an <input type="image">
                # is used.
                alt_text, image_src = field_type
                # Super-simple URL detection. Totally robust /s
                if not (image_src.startswith('http') or
                        image_src.startswith('/')):
                    image_src = flask.url_for('authn.static',
                                              filename=image_src)
                field = util.ImageField(src=image_src, alt=alt_text)
            else:
                field_text = flask_babel.gettext(field_type)
                field = wtforms.fields.SubmitField(field_text)
        fields[field_name] = field
    # Make sure there's a submit field
    if u'submit' not in fields:
        login_text = flask_babel.gettext(u"Log In")
        fields[u'submit'] = wtforms.fields.SubmitField(login_text)
    current_locale = flask_babel.get_locale()
    if current_locale is None or current_locale == 'en':
        locales = ['en']
    else:
        locales = [current_locale, 'en']
    meta = {
        'locales': locales
    }
    ProviderForm = type('ProviderForm', (flask_wtf.FlaskForm, ), fields)
    return ProviderForm


def check_second_stage(providers, app):
    # Check for in-progress, multi-stage logins (like OAuth)
    provider_in_progress = flask.session.pop('provider_in_progress', None)
    state = flask.session.pop('state', None)
    if provider_in_progress is not None:
        provider = providers[provider_in_progress]
        # Continue with the login dance
        # Check that the states match
        if flask.request.values.get('state') != state and state is not None:
            flask.abort(400)
        context_args = flask.request.values.to_dict()
        context_args['redirect_uri'] = flask.url_for('.login', _external=True)
        response = provider.create_context(**context_args)
        # success or error should be the only two possibilities
        if response['action'] == 'success':
            login_user(provider, response['context'], app)
            return True
        elif response['action'] == 'error':
            # TODO: This is totally not the right response.
            flask.abort(500)
    else:
        return False


def login_user(provider, context, app):
    store = app.store
    user_identity = provider.get_user(context)
    user = store.get_user(user_identity.user_id)
    login_user = LoginUser(user)
    flask_login.login_user(login_user)
    # TODO: Add a way to determine if a user is an admin
    # Add new character
    new_characters = provider.get_characters(context)
    for character_data in new_characters:
        try:
            character = store.get_character(character_data[u'id'])
            character.user_id = user.id_
            character.name = character_data[u'name']
            store.save_character(character)
        except storage.NotFoundError:
            character = store.add_character(user.id_,
                                            character_data[u'id'],
                                            character_data[u'name'])
    # Remove old characters
    new_character_ids = {c[u'id'] for c in new_characters}
    user_characters = store.get_characters(user.id_)
    for character in user_characters:
        if character.id_ not in new_character_ids:
            character.user_id = None
            store.save_character(character)
    # Update group memberships
    group_identities = provider.get_groups(context)
    new_group_ids = {identity.group_id for identity in group_identities}
    current_groups = store.get_groups(user.id_)
    current_group_ids = {group.id_ for group in current_groups}
    # Using the set operators. '-' is used for set difference
    add_group_ids = new_group_ids - current_group_ids
    remove_group_ids = current_group_ids - new_group_ids
    for group_id in add_group_ids:
        store.associate_user_group(user.id_, group_id)
    for group_id in remove_group_ids:
        store.disassociate_user_group(user.id_, group_id)


def redirect_next(session):
    next_url = session.get('next')
    if next_url is not None:
        if not util.is_safe_redirect(next_url):
            next_url = None
    return flask.redirect(next_url or flask.url_for('index'))


@authn_blueprint.route('/login/', methods=['GET', 'POST'])
def login():
    providers = create_providers(flask.current_app)
    if check_second_stage(providers, flask.current_app):
        return redirect_next(flask.session)
    # Create the form instances. Keys are the provider instances, values are
    # the form instances.
    forms = collections.OrderedDict()
    for provider in six.itervalues(providers):
        prefix = base64.urlsafe_b64encode(provider.uuid.bytes)
        prefix = prefix.decode('utf-8', 'replace')
        prefix = prefix.replace('=', '.')
        form = form_for_provider(provider)
        forms[provider] = form(prefix=prefix)
    # Now handle normal form processing
    if flask.request.method == 'POST':
        for provider, form in six.iteritems(forms):
            # The unique prefixes ensure only the submitted form's submit field
            # is going to be truthy
            if form.submit.data:
                break
        else:
            flask.abort(400)
        if form.validate():
            context_args = dict(form.data)
            context_args['redirect_uri'] = flask.url_for('.login',
                                                         _external=True)
            response = provider.create_context(**context_args)
            if response['action'] == 'redirect':
                # set the session so we can resume quickly
                flask.session['provider_in_progress'] = provider.uuid
                # We need to save the state somewhere so we can verify it later
                # in the second stage of oauth (oauth being the common thing
                # requiring this kind of dance).
                flask.session['state'] = response['state']
                return flask.redirect(response['url'])
            elif response['action'] == 'success':
                login_user(provider, response['context'])
                return redirect_next(flask.session)
            elif response['action'] == 'error':
                # TODO: Again, not the right response
                abort(500)
    return flask.render_template('login.html', forms=forms,
                                 title=flask_babel.gettext(u'Log In'))


@authn_blueprint.route('/logout/')
@flask_login.login_required
def logout():
    flask_login.logout_user()
    return flask.redirect(flask.url_for('index'))
