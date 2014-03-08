from flask import Flask
from flask.ext.heroku import Heroku
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
# SQLALCHEMY_DATABASE_URI gets set by the Heroku extension frmo the
# DATABASE_URL environment variable
heroku = Heroku(app)
db = SQLAlchemy(app)


