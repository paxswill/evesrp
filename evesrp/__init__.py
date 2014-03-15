from flask import Flask
from flask.ext.heroku import Heroku
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask.ext.principal import Principal

app = Flask(__name__)
# SQLALCHEMY_DATABASE_URI gets set by the Heroku extension frmo the
# DATABASE_URL environment variable
heroku = Heroku(app)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
principal = Principal(app)


