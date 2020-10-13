from __future__ import absolute_import
from decimal import Decimal
import locale
import os
import requests
import sys
import warnings
from flask import current_app, g
import flask_sqlalchemy
from flask_babel import Babel, get_locale
from flask_wtf.csrf import CsrfProtect
import six
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import MetaData
from werkzeug.utils import import_string
from .transformers import Transformer
from .versioned_static import static_file, VersionedStaticFlask

try:
    import raven.contrib.flask as raven_flask
    sentry = raven_flask.Sentry()
except ImportError:
    sentry = None


db = flask_sqlalchemy.SQLAlchemy()
# Patch Flask-SQLAlchemy to use a custom Metadata instance with a naming scheme
# for constraints.
def _patch_metadata():
    naming_convention = {
        'fk': ('fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s'
                '_%(referred_column_0_name)s'),
        'pk': 'pk_%(table_name)s',
        'ix': 'ix_%(table_name)s_%(column_0_name)s',
        'ck': 'ck_%(table_name)s_%(constraint_name)s',
        'uq': 'uq_%(table_name)s_%(column_0_name)s',
    }
    metadata = MetaData(naming_convention=naming_convention)
    base = declarative_base(cls=flask_sqlalchemy.Model, name='Model',
                            metaclass=flask_sqlalchemy._BoundDeclarativeMeta,
                            metadata=metadata)
    base.query = flask_sqlalchemy._QueryProperty(db)
    db.Model = base
_patch_metadata()

# Work around buggy HTTP servers sending out 0 length chunked responses
def _patch_httplib():
    import six.moves.http_client
    def patch_http_response_read(func):
        def inner(*args):
            try:
                return func(*args)
            except six.moves.http_client.IncompleteRead as e:
                return e.partial

        return inner
    six.moves.http_client.HTTPResponse.read = patch_http_response_read(
            six.moves.http_client.HTTPResponse.read)
_patch_httplib()

from .util import DB_STATS, AcceptRequest, WeakCiphersAdapter


__version__ = u'0.12.13.dev'


requests_session = requests.Session()


# Set default locale
locale.setlocale(locale.LC_ALL, '')


csrf = CsrfProtect()


babel = Babel()


# Ensure models are declared
from . import models
from .auth import models as auth_models
from .auth import AuthMethod


def create_app(config=None, **kwargs):
    """Create the WSGI application that is this app.

    In addition to the arguments documented below, this function accepts as a
    keyword agument all agruments to :py:class:`flask.Flask` except
    `import_name`, which is set to 'evesrp'. Additionally, the value of
    `instance_relative_config` has a default value of `True`.

    If the `config` argument isn't specified, the app will attempt to use the
    file 'config.py' in the instance folder if it exists, and will then fall
    back to using the value of the EVESRP_SETTINGS environment variable as a
    path to a config file.

    :param config: The app configuration file. Can be a Python
        :py:class:`dict`, a path to a configuration file, or an importable
        module name containing the configuration.
    :type config: str, dict
    """
    # Default instance_relative_config to True to let the config fallback work
    kwargs.setdefault('instance_relative_config', True)
    app = VersionedStaticFlask('evesrp', **kwargs)
    app.request_class = AcceptRequest
    app.config.from_object('evesrp.default_config')
    # Push the instance folder path onto sys.path to allow importing from there
    sys.path.insert(0, app.instance_path)
    # Check in config is a dict, python config file, or importable object name,
    # in that order. Finally, check the EVESRP_SETTINGS environment variable
    # as a last resort.
    if isinstance(config, dict):
        app.config.update(config)
    elif isinstance(config, six.string_types):
        if config.endswith(('.txt', '.py', '.cfg')):
            app.config.from_pyfile(config)
        else:
            app.config.from_object(config)
    elif config is None:
        try:
            app.config.from_pyfile('config.py')
        except OSError:
            app.config.from_envvar('EVESRP_SETTINGS')

    # Configure Sentry
    if 'SENTRY_DSN' in app.config or 'SENTRY_DSN' in os.environ:
        if sentry is not None:
            app.config['SENTRY_RELEASE'] = __version__
            sentry.init_app(app=app)
        else:
            app.logger.warning("SENTRY_DSN is defined but Sentry is not"
                               " installed.")

    # Register SQLAlchemy monitoring before the DB is connected
    app.before_request(sqlalchemy_before)

    db.init_app(app)

    from .views.login import login_manager
    login_manager.init_app(app)

    before_csrf = list(app.before_request_funcs[None])
    csrf.init_app(app)
    # Remove the context processor that checks CSRF values. All it is used for
    # is the template function.
    app.before_request_funcs[None] = before_csrf

    # Connect views
    from .views import index, error_page, update_navbar, divisions, login,\
            requests, api, detect_language, locale_selector
    app.add_url_rule(rule=u'/', view_func=index)
    for error_code in (400, 403, 404, 500):
        app.register_error_handler(error_code, error_page)
    app.after_request(update_navbar)
    app.register_blueprint(divisions.blueprint, url_prefix='/division')
    app.register_blueprint(login.blueprint)
    app.register_blueprint(requests.blueprint, url_prefix='/request')
    app.register_blueprint(api.api, url_prefix='/api')
    app.register_blueprint(api.filters, url_prefix='/api/filter')

    from .views import request_count
    app.add_template_global(request_count)

    from .json import SRPEncoder
    app.json_encoder=SRPEncoder

    # Hook up Babel and associated callbacks
    babel.init_app(app)
    app.before_request(detect_language)
    # localeselector can be set only once per Babel instance. Really, this will
    # only throw an exception when we're running tests. This also only became
    # an issue when they changed when Babel.locale_selector_func was changed
    # for version 0.10.
    try:
        babel.localeselector(locale_selector)
    except AssertionError:
        pass

    # Configure the Jinja context
    # Inject variables into the context
    from .auth import PermissionType
    from .util import locale as jinja_locale
    @app.context_processor
    def inject_enums():
        return {
            'ActionType': models.ActionType,
            'PermissionType': PermissionType,
            'app_version': __version__,
            'site_name': app.config['SRP_SITE_NAME'],
            'url_for_page': requests.url_for_page,
            'static_file': static_file,
            'locales': jinja_locale.enabled_locales,
            'get_locale': get_locale,
        }
    app.template_filter('currencyfmt')(jinja_locale.currencyfmt)
    app.template_filter('percentfmt')(jinja_locale.percentfmt)
    app.template_filter('numberfmt')(jinja_locale.numberfmt)
    # Auto-trim whitespace
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

    init_app(app)

    return app


def init_app(app):
    _config_requests_session(app)
    _config_url_converters(app)
    _config_authmethods(app)
    _config_killmails(app)


# SQLAlchemy performance logging
def sqlalchemy_before():
    if DB_STATS.total_queries > 0:
        current_app.logger.debug(u"{} queries in {} ms.".format(
                DB_STATS.total_queries,
                round(DB_STATS.total_time * 1000, 3)))
    DB_STATS.clear()
    g.DB_STATS = DB_STATS


# Utility function for creating instances from dicts
def _instance_from_dict(instance_descriptor):
    type_name = instance_descriptor.pop('type')
    Type = import_string(type_name)
    return Type(**instance_descriptor)


# Utility function for raising config deprecation warnings
def _deprecated_object_instance(key, value):
    warnings.warn(u"Non-basic data types in configuration values are deprecated"
                 u"({}: {})".format(key, value), DeprecationWarning,
                 stacklevel=2)


# Auth setup
def _config_authmethods(app):
    auth_methods = []
    # Once the deprecated config value support is removed, this can be
    # rewritten as a dict comprehension
    with app.app_context():
        for method in app.config['SRP_AUTH_METHODS']:
            if isinstance(method, dict):
                auth_methods.append(_instance_from_dict(method))
            elif isinstance(method, AuthMethod):
                _deprecated_object_instance('SRP_AUTH_METHODS', method)
                auth_methods.append(method)
    app.auth_methods = auth_methods


# Request detail URL setup
def _config_url_converters(app):
    url_transformers = {}
    for config_key, config_value in app.config.items():
        # Skip null config values
        if config_value is None:
            continue
        # Look for config keys in the format 'SRP_*_URL_TRANSFORMERS'
        if not config_key.endswith('_URL_TRANSFORMERS')\
                or not config_key.startswith('SRP_'):
            continue
        attribute = config_key.replace('SRP_', '', 1)
        attribute = attribute.replace('_URL_TRANSFORMERS', '', 1)
        attribute = attribute.lower()
        # Create Transformer instances for this attribute
        transformers = {}
        for transformer_config in config_value:
            if isinstance(transformer_config, tuple):
                # Special case for Transformers: A 2-tuple in the form:
                # (u'Transformer Name',
                #     'http://example.com/transformer/slug/{}')
                transformer = Transformer(*transformer_config)
            elif isinstance(transformer_config, dict):
                # Standard instance dictionary format
                # Provide a default type value
                transformer_config.setdefault('type',
                        'evesrp.transformers.Transformer')
                transformer = _instance_from_dict(transformer_config)
            elif isinstance(transformer_config, Transformer):
                # DEPRECATED: raw Transformer instance
                _deprecated_object_instance(config_key, transformer_config)
                transformer = transformer_config
            transformers[transformer.name] = transformer
        url_transformers[attribute] = transformers
    app.url_transformers = url_transformers


# Requests session setup
def _config_requests_session(app):
    try:
        ua_string = app.config['SRP_USER_AGENT_STRING']
    except KeyError as outer_exc:
        try:
            ua_string = 'EVE-SRP/{version} ({email})'.format(
                    email=app.config['SRP_USER_AGENT_EMAIL'],
                    version=__version__)
        except KeyError as inner_exc:
            raise inner_exc
    requests_session = requests.Session()
    requests_session.headers.update({'User-Agent': ua_string})
    requests_session.mount('https://crest-tq.eveonline.com',
            WeakCiphersAdapter())
    app.requests_session = requests_session


# Killmail verification
def _config_killmails(app):
    killmail_sources = []
    # For now, use a loop with checks. After removing the depecated config
    # method it can be rewritten as a list comprehension
    for source in app.config['SRP_KILLMAIL_SOURCES']:
        if isinstance(source, six.string_types):
            killmail_sources.append(import_string(source))
        elif isinstance(source, type):
            _deprecated_object_instance('SRP_KILLMAIL_SOURCES', source)
            killmail_sources.append(source)
    app.killmail_sources = killmail_sources


# Work around DBAPI-specific issues with Decimal subclasses.
# Specifically, almost everything besides pysqlite and psycopg2 raise
# exceptions if an instance of a Decimal subclass as opposed to an instance of
# Decimal itself is passed in as a value for a Numeric column.
@db.event.listens_for(Engine, 'before_execute', retval=True)
def _workaround_decimal_subclasses(conn, clauseelement, multiparams, params):
    def filter_decimal_subclasses(parameters):
        for key in six.iterkeys(parameters):
            value = parameters[key]
            # Only get instances of subclasses of Decimal, not direct
            # Decimal instances
            if type(value) != Decimal and isinstance(value, Decimal):
                parameters[key] = Decimal(value)

    if multiparams:
        for mp in multiparams:
            if isinstance(mp, dict):
                filter_decimal_subclasses(mp)
            elif isinstance(mp, list):
                for parameters in mp:
                    filter_decimal_subclasses(parameters)
    return clauseelement, multiparams, params
