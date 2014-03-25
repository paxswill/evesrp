import importlib
import locale

import requests
from flask import Flask
from flask.ext.heroku import Heroku
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext.principal import Principal

requests_session = requests.Session()
requests_session.headers.update(
        {'User-Agent': 'EVE-SRP/0.1 (paxswill@paxswill.com)'})

app = Flask('evesrp')
# SQLALCHEMY_DATABASE_URI gets set by the Heroku extension frmo the
# DATABASE_URL environment variable
heroku = Heroku(app)
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

# Views setup
from . import views

login_manager.login_view = 'login'
