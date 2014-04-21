import importlib
import locale

import requests
from flask import Flask, current_app
from flask.ext.principal import identity_loaded
from flask.ext.sqlalchemy import SQLAlchemy


requests_session = requests.Session()


# Set default locale
locale.setlocale(locale.LC_ALL, '')


db = SQLAlchemy()


def create_app(**kwargs):
    app = Flask('evesrp', **kwargs)
    app.config.from_object('evesrp.default_config')

    db.init_app(app)

    from .views.login import login_manager
    login_manager.init_app(app)

    from .auth import principal
    principal.init_app(app)

    from .views import index, divisions, login, requests
    app.add_url_rule(rule='/', view_func=index)
    app.register_blueprint(divisions.blueprint, url_prefix='/divisions')
    app.register_blueprint(login.blueprint)
    app.register_blueprint(requests.blueprint, url_prefix='/requests')

    from .auth import load_user_permissions
    identity_loaded.connect(load_user_permissions, app)

    app.before_first_request(_copy_config_to_authmethods)
    app.before_first_request(_config_requests_session)
    app.before_first_request(_config_killmails)

    return app


# Auth setup
def _copy_config_to_authmethods():
    print("configuring auth methods")
    current_app.auth_methods = []
    auth_methods = current_app.auth_methods
    for method in current_app.config['AUTH_METHODS']:
        module_name, class_name = method.rsplit('.', 1)
        module = importlib.import_module(module_name)
        method_class = getattr(module, class_name)
        auth_methods.append(method_class(config=current_app.config))


# Requests session setup
def _config_requests_session():
    try:
        ua_string = current_app.config['USER_AGENT_STRING']
    except KeyError as outer_exc:
        try:
            ua_string = 'EVE-SRP/0.1 ({})'.format(
                    current_app.config['USER_AGENT_EMAIL'])
        except KeyError as inner_exc:
            raise inner_exc from outer_exc
    requests_session.headers.update({'User-Agent': ua_string})
    current_app.user_agent = ua_string


# Killmail verification
def _config_killmails():
    current_app.killmail_sources = current_app.config['KILLMAIL_SOURCES']
