import locale
import os
import requests
from flask import Flask, current_app, g
from flask.ext.principal import identity_loaded
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.wtf.csrf import CsrfProtect


db = SQLAlchemy()


from .util import DB_STATS
from .util.request import AcceptRequest


__version__ = '0.6.1'


requests_session = requests.Session()


# Set default locale
locale.setlocale(locale.LC_ALL, '')


csrf = CsrfProtect()


# Ensure models are declared
from . import models
from .auth import models as auth_models


def create_app(config=None, **kwargs):
    app = Flask('evesrp', **kwargs)
    app.request_class = AcceptRequest
    app.config.from_object('evesrp.default_config')
    if config is not None:
        app.config.from_pyfile(config)
    if app.config['SECRET_KEY'] is None and 'SECRET_KEY' in os.environ:
        app.config['SECRET_KEY'] = os.environ['SECRET_KEY']

    # Register SQLAlchemy monitoring before the DB is connected
    app.before_request(sqlalchemy_before)

    db.init_app(app)

    from .views.login import login_manager
    login_manager.init_app(app)

    from .auth.permissions import principal, load_user_permissions
    principal.init_app(app)
    identity_loaded.connect(load_user_permissions, app)

    before_csrf = list(app.before_request_funcs[None])
    csrf.init_app(app)
    # Remove the context processor that checks CSRF values. All it is used for
    # is the template function.
    app.before_request_funcs[None] = before_csrf

    from .views import index, error_page, divisions, login, requests, api
    app.add_url_rule(rule='/', view_func=index)
    for error_code in (400, 403, 404, 500):
        app.register_error_handler(error_code, error_page)
    app.register_blueprint(divisions.blueprint, url_prefix='/division')
    app.register_blueprint(login.blueprint)
    app.register_blueprint(requests.blueprint, url_prefix='/request')
    app.register_blueprint(api.api, url_prefix='/api')
    app.register_blueprint(api.filters, url_prefix='/api/filter')

    from .views import request_count
    app.add_template_global(request_count)

    from .json import SRPEncoder
    app.json_encoder=SRPEncoder

    app.before_first_request(_copy_config_to_authmethods)
    app.before_first_request(_config_requests_session)
    app.before_first_request(_config_killmails)
    app.before_first_request(_copy_url_converter_config)

    # Configure the Jinja context
    # Inject variables into the context
    from .auth import PermissionType
    @app.context_processor
    def inject_enums():
        return {
            'ActionType': models.ActionType,
            'PermissionType': PermissionType,
        }
    # Auto-trim whitespace
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

    return app


# SQLAlchemy performance logging
def sqlalchemy_before():
    DB_STATS.clear()
    g.DB_STATS = DB_STATS


# Auth setup
def _copy_config_to_authmethods():
    current_app.auth_methods = current_app.config['AUTH_METHODS']


# Request detail URL setup
def _copy_url_converter_config():
    url_transformers = {}
    for config_key, config_value in current_app.config.items():
        if config_value is None:
            continue
        index = config_key.rfind('_URL_TRANSFORMERS')
        if not config_key.endswith('_URL_TRANSFORMERS')\
                or not config_key.startswith('SRP_'):
            continue
        attribute = config_key.replace('SRP_', '', 1)
        attribute = attribute.replace('_URL_TRANSFORMERS', '', 1)
        attribute = attribute.lower()
        url_transformers[attribute] = {t.name:t for t in config_value}
    current_app.url_transformers = url_transformers
    # temporary compatibility
    current_app.ship_urls = url_transformers.get('ship_type', None)
    current_app.pilot_urls = url_transformers.get('pilot', None)


# Requests session setup
def _config_requests_session():
    try:
        ua_string = current_app.config['USER_AGENT_STRING']
    except KeyError as outer_exc:
        try:
            ua_string = 'EVE-SRP/{version} ({email})'.format(
                    email=current_app.config['USER_AGENT_EMAIL'],
                    version=__version__)
        except KeyError as inner_exc:
            raise inner_exc from outer_exc
    requests_session.headers.update({'User-Agent': ua_string})
    current_app.user_agent = ua_string


# Killmail verification
def _config_killmails():
    current_app.killmail_sources = current_app.config['KILLMAIL_SOURCES']
