import importlib

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

# Auth setup
# Stopgap measure until I figure out how configuration should be done
method_list = ['evesrp.auth.testauth.TestAuth']
auth_methods = []
if method_list is None:
    method_list = ()
# FIXME: pull AUTH_METHODS from the configuration
for plugin in method_list:
    module_name, method = plugin.rsplit('.', 1)
    module = importlib.import_module(module_name)
    auth_methods.append(module.__dict__[method])


# Views setup
from . import views

login_manager.login_view = 'login'
