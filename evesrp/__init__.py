import importlib
import locale

import requests
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext.principal import Principal

requests_session = requests.Session()

app = Flask('evesrp')
# SQLALCHEMY_DATABASE_URI gets set by the Heroku extension frmo the
# DATABASE_URL environment variable
db = SQLAlchemy(app)
login_manager = LoginManager(app)
principal = Principal(app)

# Set default locale
locale.setlocale(locale.LC_ALL, '')

# Auth setup
auth_methods = []
@app.before_first_request
def _copy_config_to_authmethods():
    for method in app.config['AUTH_METHODS']:
        module_name, class_name = method.rsplit('.', 1)
        module = importlib.import_module(module_name)
        method_class = getattr(module, class_name)
        auth_methods.append(method_class(config=app.config))


# Requests session setup
user_agent = ''
@app.before_first_request
def _config_requests_session():
    try:
        ua_string = app.config['USER_AGENT_STRING']
    except KeyError as outer_exc:
        try:
            ua_string = 'EVE-SRP/0.1 ({})'.format(
                    app.config['USER_AGENT_EMAIL'])
        except KeyError as inner_exc:
            raise inner_exc from outer_exc
    requests_session.headers.update({'User-Agent': ua_string})
    user_agent = ua_string


# Killmail verification
killmail_sources = []
@app.before_first_request
def _config_killmails():
    killmail_sources.extend(app.config['KILLMAIL_SOURCES'])


# Views setup
from . import views
from .views import divisions

login_manager.login_view = 'login'
